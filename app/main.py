# app/main.py
import os
import time
from datetime import datetime

from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import StreamingResponse, JSONResponse

# Import services
from config import config
from models import create_tables
from services.database_service import DatabaseService
from services.file_service import FileService
from services.ollama_service import OllamaService
from services.context_service import ContextService

# Initialize
config.ensure_directories()
create_tables()

# Initialize services
db_service = DatabaseService()
file_service = FileService()
ollama_service = OllamaService()
context_service = ContextService()

app = FastAPI(title="Gemma Agent with Streaming & pgvector Context")


@app.post("/upload-image")
async def upload_image(file: UploadFile = File(...), prompt: str = Form("Describe the image")):
    """
    Endpoint that (1) saves a placeholder DB record, (2) processes the model output fully (no streaming),
    and (3) updates the DB with final response & embedding before returning the complete result as JSON.
    """
    contents = await file.read()
    filename = file_service.save_uploaded_file(contents, file.filename)

    # Convert image to Base64 for Ollama
    b64 = ollama_service.image_to_base64_bytes(contents)

    # Build context using pgvector or FAISS (whichever your context_service uses)
    context_text = context_service.build_context_from_prompt(prompt)

    # Create initial DB records
    image_id = db_service.create_image_record(filename)
    db_service.create_interaction_record(image_id, prompt)

    try:
        # Get the complete model response (non-streaming)
        model_response = ollama_service.get_complete_response(
            b64, prompt, context_text)

        # Compute embeddings for response + prompt
        embedding_bytes = None
        try:
            if model_response:
                emembedding_array = ollama_service.call_ollama_embed(
                    model_response + "\n" + prompt)
        except Exception:
            embedding_bytes = None

        # Update DB records with final model output & embedding
        db_service.update_image_with_response(
            image_id, model_response, embedding_bytes)
        db_service.update_interaction_response(image_id, model_response)

        # Return final structured response
        return JSONResponse({
            "success": True,
            "image_id": image_id,
            "response": model_response,
            "context": context_text if context_text else "No relevant context found from previous images",
            "filename": filename
        })

    except Exception as e:
        # Handle model or embedding errors
        error_msg = f"Error processing image: {str(e)}"
        db_service.update_image_with_response(image_id, error_msg, None)
        db_service.update_interaction_response(image_id, error_msg)

        return JSONResponse({
            "success": False,
            "error": error_msg,
            "image_id": image_id,
            "context": context_text if context_text else "No relevant context found from previous images"
        }, status_code=500)

@app.get("/images")
def list_images():
    return db_service.get_all_images()


@app.get("/image/{image_id}")
def get_image(image_id: int):
    result = db_service.get_image_by_id(image_id)
    if not result:
        return JSONResponse({"error": "not found"}, status_code=404)
    return result


@app.get("/health")
def health_check():
    return {"status": "healthy"}
