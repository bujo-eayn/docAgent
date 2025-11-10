"""FastAPI application for document-based chat with RAG.

This module provides the main FastAPI application with endpoints for:
- Creating chat sessions by uploading documents
- Sending messages and getting AI responses
- Managing chat sessions (list, retrieve, delete)
- Health checking
"""

import json
import os
from typing import Generator

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse

# Import services and configuration
from config import config
from constants import (
    CHAT_SYSTEM_PROMPT_TEMPLATE,
    ROLE_ASSISTANT,
    ROLE_SYSTEM,
    ROLE_USER,
)
from exceptions import ChatNotFoundException, DocumentProcessingException
from models import create_tables
from services.chat_service import ChatService
from services.context_service import ContextService
from services.document_processor import DocumentProcessor
from services.file_service import FileService
from services.ollama_service import OllamaService
from utils.logger import setup_logger

logger = setup_logger(__name__)

# Initialize
config.ensure_directories()
create_tables()

# Initialize services
chat_service = ChatService()
file_service = FileService()
ollama_service = OllamaService()
context_service = ContextService()
document_processor = DocumentProcessor()

app = FastAPI(
    title="Document Chat Agent with Context Extraction",
    description="RAG-based chat system for document question answering",
    version="2.0.0",
)


# Exception handlers
@app.exception_handler(ChatNotFoundException)
async def chat_not_found_handler(request, exc: ChatNotFoundException):
    """Handle ChatNotFoundException with 404 response."""
    return JSONResponse(status_code=404, content={"detail": exc.message, **exc.details})


@app.exception_handler(DocumentProcessingException)
async def document_processing_handler(request, exc: DocumentProcessingException):
    """Handle DocumentProcessingException with 500 response."""
    return JSONResponse(status_code=500, content={"detail": exc.message, **exc.details})


@app.post("/chats/create")
async def create_new_chat(file: UploadFile = File(...)):
    """
    Create a new chat session by uploading a document image.
    Extracts all information from the document and stores as searchable context.
    """
    try:
        # Save the uploaded document
        contents = await file.read()
        filename = file_service.save_uploaded_file(contents, file.filename)
        document_path = os.path.join(config.images_dir, filename)

        # Create chat session
        chat_id = chat_service.create_chat(
            document_filename=file.filename, document_path=document_path
        )

        # Convert image to base64 for Ollama
        b64 = ollama_service.image_to_base64_bytes(contents)

        # Process document: extract info, chunk, embed, and store
        extracted_text, chunk_count = document_processor.process_document(chat_id, b64)

        # Add system message indicating document was processed
        chat_service.add_message(
            chat_id=chat_id,
            role=ROLE_SYSTEM,
            content=f"Document '{file.filename}' uploaded and processed. Extracted {chunk_count} context chunks. Ready for questions!",
        )

        return {
            "success": True,
            "chat_id": chat_id,
            "message": "Chat created and document processed successfully",
            "document_filename": file.filename,
            "chunks_created": chunk_count,
        }

    except DocumentProcessingException as e:
        logger.error(f"Document processing failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error processing document: {e.message}"
        )
    except Exception as e:
        logger.error(f"Unexpected error creating chat: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error creating chat: {str(e)}")


@app.post("/chats/{chat_id}/message")
async def send_message(chat_id: int, question: str = Form(...)):
    """
    Send a message/question within a chat.
    Retrieves relevant context from the chat's document and streams response.
    """
    # Verify chat exists
    chat = chat_service.get_chat(chat_id)
    if not chat:
        logger.warning(f"Chat {chat_id} not found")
        raise ChatNotFoundException(chat_id)

    # Add user message
    chat_service.add_message(chat_id=chat_id, role=ROLE_USER, content=question)

    # Build context from the chat's document
    context_text = context_service.build_context_from_query(
        chat_id, question, top_k=config.top_k_contexts
    )

    # Stream response from Ollama
    def event_generator() -> Generator[str, None, None]:
        """Generate streaming response with context."""
        collected_fragments = []

        try:
            # Build system prompt with context
            system_prompt = CHAT_SYSTEM_PROMPT_TEMPLATE.format(context=context_text)

            # Stream response
            for chunk in ollama_service.stream_ollama_chat(question, system_prompt):
                yield chunk
                if chunk.startswith("data:"):
                    payload = chunk[len("data:") :].strip()
                    if payload != "[DONE]":
                        collected_fragments.append(payload)

            final_response = "".join(collected_fragments).strip()

        except Exception as e:
            logger.error(f"Error streaming response: {e}", exc_info=True)
            final_response = f"[ERROR] {str(e)}"

        # Save assistant response with context used
        chat_service.add_message(
            chat_id=chat_id,
            role=ROLE_ASSISTANT,
            content=final_response,
            context_used=context_text if context_text else None,
        )

        # Send final metadata
        final_data = json.dumps(
            {"final": final_response, "context": context_text, "chat_id": chat_id}
        )
        yield f"data: {final_data}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/chats")
def list_chats():
    """Get all chat sessions"""
    return chat_service.get_all_chats()


@app.get("/chats/{chat_id}")
def get_chat_details(chat_id: int):
    """Get chat details with all messages.

    Args:
        chat_id: ID of the chat to retrieve

    Returns:
        Chat object with messages array

    Raises:
        ChatNotFoundException: If chat ID does not exist
    """
    chat = chat_service.get_chat(chat_id)
    if not chat:
        raise ChatNotFoundException(chat_id)

    messages = chat_service.get_chat_messages(chat_id)
    chat["messages"] = messages
    return chat


@app.delete("/chats/{chat_id}")
def delete_chat(chat_id: int):
    """Delete a chat session (soft delete).

    Args:
        chat_id: ID of the chat to delete

    Returns:
        Success confirmation

    Raises:
        ChatNotFoundException: If chat ID does not exist
    """
    success = chat_service.delete_chat(chat_id)
    if not success:
        raise ChatNotFoundException(chat_id)
    return {"success": True, "message": "Chat deleted"}


@app.get("/health")
def health_check():
    """Health check endpoint.

    Returns:
        Status object indicating application health
    """
    return {"status": "healthy"}
