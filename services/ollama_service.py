# services/ollama_service.py
import base64
import json
import numpy as np
import requests
from config import config


class OllamaService:
    def __init__(self):
        self.base_url = config.OLLAMA_URL
        self.model_name = config.MODEL_NAME

    def image_to_base64_bytes(self, file_bytes: bytes) -> str:
        return base64.b64encode(file_bytes).decode("utf-8")

    def call_ollama_embed(self, text: str):
        """
        Call Ollama embed endpoint. Try /api/embed, then /api/embeddings.
        Returns np.array(dtype=float32) if successful, else raises.
        """
        for endpoint in ["/api/embed", "/api/embeddings"]:
            try:
                url = f"{self.base_url}{endpoint}"
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

    def stream_ollama_chat_with_image(self, image_b64: str, user_message: str, context: str):
        """
        Stream tokens from Ollama /api/chat in a blocking generator.
        The generator yields SSE-like lines: "data: <token>\n\n".
        """
        url = f"{self.base_url}/api/chat"
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
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message,
                    "images": [image_b64]},
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
