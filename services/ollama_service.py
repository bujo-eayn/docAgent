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

    def get_complete_response(self, image_b64: str, user_message: str, context: str) -> str:
        """
        Get complete response from Ollama /api/chat (non-streaming).
        Returns the complete response text.
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
            "stream": False,  # Important: set stream to False for complete response
        }

        # Make non-streaming request
        r = requests.post(url, json=payload, timeout=300)
        r.raise_for_status()

        response_data = r.json()

        # Extract the complete message content
        if isinstance(response_data, dict):
            message = response_data.get("message", {})
            if isinstance(message, dict):
                return message.get("content", "")

        return ""

    def stream_ollama_chat_with_image(self, image_b64: str, user_message: str, context: str):
        """
        Stream tokens from Ollama /api/chat in a blocking generator.
        The generator yields SSE-like lines: "data: <token>\n\n".
        (Keeping this method for backward compatibility if needed)
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

        # Use requests streaming
        with requests.post(url, json=payload, stream=True, timeout=300) as r:
            r.raise_for_status()
            for raw_line in r.iter_lines():
                if not raw_line:
                    continue
                try:
                    line = raw_line.decode("utf-8").strip()
                except Exception:
                    continue

                if not line:
                    continue

                # Parse the JSON response from Ollama
                try:
                    parsed = json.loads(line)
                    if isinstance(parsed, dict):
                        # Check if this is the final response
                        if parsed.get("done", False):
                            yield "data: [DONE]\n\n"
                            break

                        # Extract content from message
                        message = parsed.get("message", {})
                        if isinstance(message, dict):
                            content = message.get("content", "")
                            if content:
                                # Yield the content token
                                yield f"data: {content}\n\n"
                except json.JSONDecodeError:
                    # If not valid JSON, skip this line
                    continue
