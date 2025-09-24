# app/main.py
import os
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

app = FastAPI(title="Gemma Agent with Streaming & FAISS Context")


@app.post("/upload-image-stream")
async def upload_image_stream(file: UploadFile = File(...), prompt: str = Form("Describe the image")):
    """
    Endpoint that (1) saves a placeholder DB record, (2) streams the model's Plan/Reason/Evaluate
    output back to the client as SSE-like text, and (3) updates the DB with final response & embedding.
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

    # Generator that streams model output and collects full text for DB update
    def event_generator():
        collected_fragments = []
        try:
            for s in ollama_service.stream_ollama_chat_with_image(b64, prompt, context_text):
                # forward to client
                yield s
                # collect token fragments, but ignore the [DONE] marker
                if s.startswith("data:"):
                    payload = s[len("data:"):].strip()
                    if payload != "[DONE]":
                        collected_fragments.append(payload)
            # After finishing, build final response text
            final_text = "".join(collected_fragments).strip()
        except Exception as e:
            # If streaming fails, still update DB with error message
            final_text = f"[STREAMING ERROR] {str(e)}"

        # Attempt to compute embedding for final text + prompt
        embedding_bytes = None
        try:
            if final_text:
                emb = ollama_service.call_ollama_embed(
                    final_text + "\n" + prompt)
                embedding_bytes = emb.tobytes()
        except Exception:
            embedding_bytes = None

        # Update DB records with final response & embedding (if any)
        try:
            db_service.update_image_with_response(
                image_id, final_text, embedding_bytes)
            db_service.update_interaction_response(image_id, final_text)
        except Exception:
            # Swallow DB update errors but don't crash streaming
            pass

        # Send final response and image_id to frontend
        import json
        final_data = json.dumps({"final": final_text, "image_id": image_id})
        yield f"data: {final_data}\n\n"

        # Final marker to client
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/images")
def list_images():
    return db_service.get_all_images()


@app.get("/image/{image_id}")
def get_image(image_id: int):
    result = db_service.get_image_by_id(image_id)
    if not result:
        return JSONResponse({"error": "not found"}, status_code=404)
    return result
