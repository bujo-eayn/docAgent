# services/ollama_service.py
"""Ollama service for LLM and embedding operations.

This service provides integration with the Ollama API for:
- Text embeddings generation
- Chat completions with streaming
- Image-based chat completions
"""
import base64
import json
from typing import Any, Dict, Generator, List, Optional

import numpy as np
import requests

from config import config
from constants import (
    EMBEDDING_MODEL_NAME,
    STREAM_DATA_PREFIX,
    STREAM_DONE_MARKER,
)
from exceptions import EmbeddingException, OllamaServiceException
from utils.logger import setup_logger

logger = setup_logger(__name__)


class OllamaService:
    """Service for interacting with Ollama API."""

    def __init__(self):
        """Initialize Ollama service with configuration."""
        self.base_url = config.ollama_url
        self.model_name = config.model_name
        self.embedding_model = config.embedding_model_name

    def image_to_base64_bytes(self, file_bytes: bytes) -> str:
        """Convert image bytes to base64 string for Ollama API.

        Args:
            file_bytes: Raw image file bytes

        Returns:
            Base64 encoded string representation of the image
        """
        return base64.b64encode(file_bytes).decode("utf-8")

    def call_ollama_embed(self, text: str) -> np.ndarray:
        """Generate embeddings for text using Ollama.

        Tries multiple API endpoints for compatibility with different Ollama versions.

        Args:
            text: Text to generate embeddings for

        Returns:
            Numpy array of embeddings (1024 dimensions, float32)

        Raises:
            EmbeddingException: If embedding generation fails
        """
        last_exc = None
        for endpoint in ["/api/embed", "/api/embeddings"]:
            try:
                url = f"{self.base_url}{endpoint}"
                payload = {"model": self.embedding_model, "input": text}
                response = requests.post(
                    url, json=payload, timeout=config.embed_timeout
                )
                response.raise_for_status()
                data = response.json()

                # Handle different response formats
                if isinstance(data, dict) and "embeddings" in data:
                    vec = data["embeddings"][0]
                elif isinstance(data, dict) and "embedding" in data:
                    vec = data["embedding"]
                else:
                    vec = data.get("data", [{}])[0].get("embedding")

                if vec is None:
                    raise ValueError("No embedding returned from API")

                return np.array(vec, dtype=np.float32)

            except Exception as e:
                last_exc = e
                logger.warning(f"Embedding endpoint {endpoint} failed: {e}")
                continue

        # All endpoints failed
        error_msg = f"All embedding endpoints failed. Last error: {last_exc}"
        logger.error(error_msg)
        raise EmbeddingException(text_preview=text[:100], reason=str(last_exc))

    def _stream_ollama_response(
        self, messages: List[Dict[str, Any]], timeout: int = None
    ) -> Generator[str, None, None]:
        """Internal method to stream Ollama chat responses.

        Args:
            messages: List of message dictionaries for Ollama API
            timeout: Request timeout in seconds (default: from config)

        Yields:
            SSE-formatted strings with content tokens

        Raises:
            OllamaServiceException: If streaming fails
        """
        url = f"{self.base_url}/api/chat"
        timeout = timeout or config.chat_timeout

        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": True,
        }

        try:
            with requests.post(
                url, json=payload, stream=True, timeout=timeout
            ) as response:
                response.raise_for_status()

                for raw_line in response.iter_lines():
                    if not raw_line:
                        continue

                    try:
                        line = raw_line.decode("utf-8").strip()
                    except UnicodeDecodeError:
                        logger.warning("Failed to decode response line")
                        continue

                    if not line:
                        continue

                    # Parse JSON response from Ollama
                    try:
                        parsed = json.loads(line)
                        if not isinstance(parsed, dict):
                            continue

                        # Check if streaming is complete
                        if parsed.get("done", False):
                            yield f"{STREAM_DATA_PREFIX} {STREAM_DONE_MARKER}\n\n"
                            break

                        # Extract content from message
                        message = parsed.get("message", {})
                        if isinstance(message, dict):
                            content = message.get("content", "")
                            if content:
                                yield f"{STREAM_DATA_PREFIX} {content}\n\n"

                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse JSON: {line[:100]}")
                        continue

        except requests.exceptions.RequestException as e:
            logger.error(f"Ollama streaming request failed: {e}")
            raise OllamaServiceException(endpoint=url, reason=str(e))

    def stream_ollama_chat(
        self, user_message: str, system_prompt: str
    ) -> Generator[str, None, None]:
        """Stream chat response for text-only conversation.

        Args:
            user_message: The user's question or message
            system_prompt: System prompt with context and instructions

        Yields:
            SSE-formatted strings with response tokens

        Raises:
            OllamaServiceException: If streaming fails
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        yield from self._stream_ollama_response(messages)

    def stream_ollama_chat_with_image(
        self, image_b64: str, user_message: str, context: str
    ) -> Generator[str, None, None]:
        """Stream chat response with image input.

        Args:
            image_b64: Base64-encoded image
            user_message: The user's question or message
            context: Context information to include in system prompt

        Yields:
            SSE-formatted strings with response tokens

        Raises:
            OllamaServiceException: If streaming fails
        """
        system_prompt = (
            "You are a structured reasoning assistant. Follow this format exactly:\n\n"
            "PLAN: Provide a short numbered plan of steps you will take.\n\n"
            "REASON: Work through the observations, produce reasoning and details.\n\n"
            "EVALUATE: Summarize the final conclusion briefly.\n\n"
            "If the CONTEXT section is provided, consult it and reference relevant parts.\n\n"
            f"CONTEXT:\n{context}\n\n"
            "Respond in plain text following PLAN / REASON / EVALUATE sections."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message, "images": [image_b64]},
        ]

        yield from self._stream_ollama_response(messages)
