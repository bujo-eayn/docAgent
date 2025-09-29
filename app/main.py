# app/main.py
import os
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import JSONResponse

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

app = FastAPI(title="Gemma Agent with FAISS Context")


@app.post("/upload-image")
async def upload_image(file: UploadFile = File(...), prompt: str = Form("Describe the image")):
    """
    Endpoint that processes the image completely and returns the full response with context.
    No streaming - waits for complete model response.
    """
    contents = await file.read()
    filename = file_service.save_uploaded_file(contents, file.filename)

    # Base64 for Ollama
    b64 = ollama_service.image_to_base64_bytes(contents)

    # Build context using FAISS
    context_text = context_service.build_context_from_prompt(prompt)

    # Create database records
    image_id = db_service.create_image_record(filename)
    db_service.create_interaction_record(image_id, prompt)

    try:
        # Get complete response from model (non-streaming)
        model_response = ollama_service.get_complete_response(
            b64, prompt, context_text)

        # Compute embedding for final text + prompt
        embedding_bytes = None
        try:
            if model_response:
                emb = ollama_service.call_ollama_embed(
                    model_response + "\n" + prompt)
                embedding_bytes = emb.tobytes()
        except Exception:
            embedding_bytes = None

        # Update DB records with final response & embedding
        db_service.update_image_with_response(
            image_id, model_response, embedding_bytes)
        db_service.update_interaction_response(image_id, model_response)

        return JSONResponse({
            "success": True,
            "image_id": image_id,
            "response": model_response,
            "context": context_text if context_text else "No relevant context found from previous images",
            "filename": filename
        })

    except Exception as e:
        error_msg = f"Error processing image: {str(e)}"
        # Update DB with error
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
