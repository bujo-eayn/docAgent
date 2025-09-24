# app/main.py
import base64
import json
import os
import time
from datetime import datetime

import numpy as np
import requests
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy import (Column, DateTime, Integer, LargeBinary, MetaData,
                        String, Table, create_engine, insert, select, update)

# if running as package 'app'
from app.faiss_indexer import build_index, search_index

# CONFIG
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
MODEL_NAME = os.environ.get("MODEL_NAME", "gemma3")
BASE_DIR = os.environ.get("DATA_DIR", "./data")
IMAGES_DIR = os.path.join(BASE_DIR, "images")
DB_PATH = os.path.join(BASE_DIR, "memory.db")
os.makedirs(IMAGES_DIR, exist_ok=True)
os.makedirs(BASE_DIR, exist_ok=True)

# Simple SQLite using SQLAlchemy Core
engine = create_engine(
    f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
metadata = MetaData()

images_tbl = Table(
    "images", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("filename", String, nullable=False),
    Column("caption", String, nullable=True),
    Column("embedding", LargeBinary, nullable=True),
    Column("created_at", DateTime, default=datetime.utcnow),
)

interactions_tbl = Table(
    "interactions", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("image_id", Integer, nullable=True),
    Column("user_prompt", String, nullable=True),
    Column("model_response", String, nullable=True),
    Column("created_at", DateTime, default=datetime.utcnow),
)

metadata.create_all(engine)

app = FastAPI(title="Gemma Agent with Streaming & FAISS Context")


def image_to_base64_bytes(file_bytes: bytes) -> str:
    return base64.b64encode(file_bytes).decode("utf-8")


def call_ollama_embed(text: str):
    """
    Call Ollama embed endpoint. Try /api/embed, then /api/embeddings.
    Returns np.array(dtype=float32) if successful, else raises.
    """
    for endpoint in ["/api/embed", "/api/embeddings"]:
        try:
            url = f"{OLLAMA_URL}{endpoint}"
            payload = {"model": "nomic-embed-text", "input": text}
            r = requests.post(url, json=payload, timeout=30)
            r.raise_for_status()
            out = r.json()
            if isinstance(out, dict) and "embeddings" in out:
                vec = out["embeddings"][0]
            elif isinstance(out, dict) and "embedding" in out:
                vec = out["embedding"]
            else:
                vec = out.get("data", [{}])[0].get("embedding")
            if vec is None:
                raise ValueError("No embedding returned")
            return np.array(vec, dtype=np.float32)
        except Exception as e:
            last_exc = e
            continue
    raise last_exc


def stream_ollama_chat_with_image(image_b64: str, user_message: str, context: str):
    """
    Stream tokens from Ollama /api/chat in a blocking generator.
    The generator yields SSE-like lines: "data: <token>\n\n".
    """
    url = f"{OLLAMA_URL}/api/chat"
    system_prompt = (
        "You are a structured reasoning assistant. Follow this format exactly:\n\n"
        "PLAN: Provide a short numbered plan of steps you will take.\n\n"
        "REASON: Work through the observations, produce reasoning and details.\n\n"
        "EVALUATE: Summarize the final conclusion briefly.\n\n"
        "If the CONTEXT section is provided, consult it and reference relevant parts.\n\n"
        f"CONTEXT:\n{context}\n\n"
        "Respond in plain text following PLAN / REASON / EVALUATE sections."
    )

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message, "images": [image_b64]},
        ],
        "stream": True,
    }

    # Use requests streaming; Ollama will likely stream JSON lines prefixed with "data: "
    with requests.post(url, json=payload, stream=True, timeout=300) as r:
        r.raise_for_status()
        for raw_line in r.iter_lines():
            if not raw_line:
                continue
            try:
                line = raw_line.decode("utf-8")
            except Exception:
                line = str(raw_line)
            # Ollama streaming often uses leading "data: " lines
            if line.startswith("data:"):
                chunk = line[len("data:"):].strip()
            else:
                chunk = line.strip()

            if not chunk:
                continue

            if chunk == "[DONE]":
                # Signal end of stream to client
                yield "data: [DONE]\n\n"
                break

            # Try to parse JSON chunk to find message content
            token_text = None
            try:
                parsed = json.loads(chunk)
                # Common fields in streaming chunks
                if isinstance(parsed, dict):
                    # Some Ollama versions emit {"message": {"content": "<...>"}}
                    msg = parsed.get("message") or parsed.get(
                        "choices", [{}])[0].get("message")
                    if isinstance(msg, dict):
                        token_text = msg.get("content")
                    # older style: {"response": "..."} or {"text": "..."}
                    if not token_text:
                        token_text = parsed.get(
                            "response") or parsed.get("text")
                else:
                    token_text = str(parsed)
            except Exception:
                # fallback: treat chunk as raw text token
                token_text = chunk

            if token_text:
                # Yield as SSE-like payload (the frontend expects lines beginning with "data:")
                # Note we yield token_text directly — the frontend appends sequentially.
                yield f"data: {token_text}\n\n"


@app.post("/upload-image-stream")
async def upload_image_stream(file: UploadFile = File(...), prompt: str = Form("Describe the image")):
    """
    Endpoint that (1) saves a placeholder DB record, (2) streams the model's Plan/Reason/Evaluate
    output back to the client as SSE-like text, and (3) updates the DB with final response & embedding.
    """
    contents = await file.read()
    timestamp = int(time.time() * 1000)
    filename = f"{timestamp}_{file.filename}"
    path = os.path.join(IMAGES_DIR, filename)
    with open(path, "wb") as f:
        f.write(contents)

    # Base64 for Ollama
    b64 = image_to_base64_bytes(contents)

    # Build context using FAISS: embed the prompt, search top-2 captions (if possible)
    context_text = ""
    try:
        query_vec = call_ollama_embed(prompt)
        index, ids_with_caps = build_index()
        if index is not None and ids_with_caps is not None:
            neighbors = search_index(index, ids_with_caps, query_vec, top_k=2)
            if neighbors:
                # assemble simple bullet context
                context_text = "\n".join(
                    [f"- {n['caption']}" for n in neighbors if n.get("caption")])
    except Exception:
        context_text = ""

    # Insert placeholder record(s) so we have image_id to update later
    with engine.begin() as conn:
        res = conn.execute(
            insert(images_tbl).values(
                filename=filename,
                caption=None,
                embedding=None,
                created_at=datetime.utcnow(),
            )
        )
        image_id = res.inserted_primary_key[0]
        conn.execute(
            insert(interactions_tbl).values(
                image_id=image_id,
                user_prompt=prompt,
                model_response=None,
                created_at=datetime.utcnow(),
            )
        )

    # Generator that streams model output and collects full text for DB update
    def event_generator():
        collected_fragments = []
        try:
            for s in stream_ollama_chat_with_image(b64, prompt, context_text):
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
                emb = call_ollama_embed(final_text + "\n" + prompt)
                embedding_bytes = emb.tobytes()
        except Exception:
            embedding_bytes = None

        # Update DB records with final response & embedding (if any)
        try:
            with engine.begin() as conn:
                conn.execute(
                    images_tbl.update()
                    .where(images_tbl.c.id == image_id)
                    .values(caption=final_text, embedding=embedding_bytes)
                )
                conn.execute(
                    interactions_tbl.update()
                    .where(interactions_tbl.c.image_id == image_id)
                    .values(model_response=final_text)
                )
        except Exception:
            # Swallow DB update errors but don't crash streaming
            pass

        # Final marker to client (redundant if Ollama already sent [DONE])
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/images")
def list_images():
    with engine.connect() as conn:
        rows = conn.execute(select(images_tbl)).fetchall()
        items = []
        for r in rows:
            items.append(
                {"id": r.id, "filename": r.filename, "caption": r.caption,
                    "created_at": r.created_at.isoformat()}
            )
    return items


@app.get("/image/{image_id}")
def get_image(image_id: int):
    with engine.connect() as conn:
        r = conn.execute(select(images_tbl).where(
            images_tbl.c.id == image_id)).first()
        if not r:
            return JSONResponse({"error": "not found"}, status_code=404)
        return {"id": r.id, "filename": r.filename, "caption": r.caption, "created_at": r.created_at.isoformat()}
