# app/main.py - Complete Redesign for Chat-Based Workflow
import os
import time
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse

# Import services
from config import config
from models import create_tables
from services.chat_service import ChatService
from services.file_service import FileService
from services.ollama_service import OllamaService
from services.context_service import ContextService
from services.document_processor import DocumentProcessor

# Initialize
config.ensure_directories()
create_tables()

# Initialize services
chat_service = ChatService()
file_service = FileService()
ollama_service = OllamaService()
context_service = ContextService()
document_processor = DocumentProcessor()

app = FastAPI(title="Document Chat Agent with Context Extraction")


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
        document_path = os.path.join(config.IMAGES_DIR, filename)

        # Create chat session
        chat_id = chat_service.create_chat(
            document_filename=file.filename,
            document_path=document_path
        )

        # Convert image to base64 for Ollama
        b64 = ollama_service.image_to_base64_bytes(contents)

        # Process document: extract info, chunk, embed, and store
        extracted_text, chunk_count = document_processor.process_document(
            chat_id, b64)

        # Add system message indicating document was processed
        chat_service.add_message(
            chat_id=chat_id,
            role="system",
            content=f"Document '{file.filename}' uploaded and processed. Extracted {chunk_count} context chunks. Ready for questions!"
        )

        return {
            "success": True,
            "chat_id": chat_id,
            "message": "Chat created and document processed successfully",
            "document_filename": file.filename,
            "chunks_created": chunk_count
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error creating chat: {str(e)}")


@app.post("/chats/{chat_id}/message")
async def send_message(chat_id: int, question: str = Form(...)):
    """
    Send a message/question within a chat.
    Retrieves relevant context from the chat's document and streams response.
    """
    # Verify chat exists
    chat = chat_service.get_chat(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    # Add user message
    chat_service.add_message(chat_id=chat_id, role="user", content=question)

    # Build context from the chat's document
    context_text = context_service.build_context_from_query(
        chat_id, question, top_k=3)

    # Stream response from Ollama
    def event_generator():
        collected_fragments = []
        try:
            system_prompt = f"""You are a helpful assistant answering questions about a document. Use the provided CONTEXT to answer questions accurately.

CONTEXT FROM DOCUMENT:
{context_text}

Answer the user's question based on this context. If the context doesn't contain relevant information, say so clearly."""

            # Stream response
            for s in ollama_service.stream_ollama_chat(question, system_prompt):
                yield s
                if s.startswith("data:"):
                    payload = s[len("data:"):].strip()
                    if payload != "[DONE]":
                        collected_fragments.append(payload)

            final_response = "".join(collected_fragments).strip()
        except Exception as e:
            final_response = f"[ERROR] {str(e)}"

        # Save assistant response with context used
        chat_service.add_message(
            chat_id=chat_id,
            role="assistant",
            content=final_response,
            context_used=context_text if context_text else None
        )

        # Send final metadata
        import json
        final_data = json.dumps({
            "final": final_response,
            "context": context_text,
            "chat_id": chat_id
        })
        yield f"data: {final_data}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/chats")
def list_chats():
    """Get all chat sessions"""
    return chat_service.get_all_chats()


@app.get("/chats/{chat_id}")
def get_chat_details(chat_id: int):
    """Get chat details with all messages"""
    chat = chat_service.get_chat(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    messages = chat_service.get_chat_messages(chat_id)
    chat["messages"] = messages
    return chat


@app.delete("/chats/{chat_id}")
def delete_chat(chat_id: int):
    """Delete a chat session"""
    success = chat_service.delete_chat(chat_id)
    if not success:
        raise HTTPException(status_code=404, detail="Chat not found")
    return {"success": True, "message": "Chat deleted"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
