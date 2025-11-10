# services/document_processor.py - Document Processing Service
"""Document processor service for extracting, chunking, and embedding documents.

This service handles the complete pipeline for processing uploaded documents:
1. Extract all information from document images using LLM
2. Chunk the extracted text into manageable pieces
3. Generate embeddings for each chunk
4. Store chunks with embeddings in the database
"""
import re
from typing import List, Tuple

import requests

from config import config
from constants import DOCUMENT_EXTRACTION_PROMPT
from exceptions import DocumentProcessingException
from services.chat_service import ChatService
from services.ollama_service import OllamaService
from utils.logger import setup_logger

logger = setup_logger(__name__)


class DocumentProcessor:
    """Service to handle document processing: extraction, chunking, embedding, and storage."""

    def __init__(self):
        """Initialize document processor with required services."""
        self.ollama_service = OllamaService()
        self.chat_service = ChatService()

    def extract_information_from_image(self, image_b64: str) -> str:
        """Extract ALL information from a document image using LLM.

        Args:
            image_b64: Base64-encoded image of the document

        Returns:
            Comprehensive text extraction of all visible information

        Raises:
            DocumentProcessingException: If extraction fails
        """
        url = f"{self.ollama_service.base_url}/api/chat"
        payload = {
            "model": self.ollama_service.model_name,
            "messages": [
                {"role": "system", "content": DOCUMENT_EXTRACTION_PROMPT},
                {
                    "role": "user",
                    "content": "Extract all information from this image.",
                    "images": [image_b64],
                },
            ],
            "stream": False,  # Non-streaming for extraction
        }

        try:
            response = requests.post(
                url, json=payload, timeout=config.extraction_timeout
            )
            response.raise_for_status()

            result = response.json()
            message = result.get("message", {})
            content = message.get("content", "")

            if not content:
                raise ValueError("No content extracted from image")

            return content

        except Exception as e:
            logger.error(f"Failed to extract information from image: {e}")
            raise DocumentProcessingException(
                filename="image", reason=f"Extraction failed: {str(e)}"
            )

    def chunk_text(
        self, text: str, chunk_size: int = None, overlap: int = None
    ) -> List[str]:
        """Split extracted text into overlapping chunks for better context retrieval.

        Args:
            text: The text to chunk
            chunk_size: Maximum size of each chunk in characters (default: from config)
            overlap: Number of characters to overlap between chunks (default: from config)

        Returns:
            List of text chunks with overlap
        """
        chunk_size = chunk_size or config.chunk_size
        overlap = overlap or config.chunk_overlap

        # Split by sentences to maintain coherence
        sentences = re.split(r"(?<=[.!?])\s+", text)

        chunks = []
        current_chunk = []
        current_length = 0

        for sentence in sentences:
            sentence_length = len(sentence)

            # If adding this sentence exceeds chunk_size, save current chunk
            if current_length + sentence_length > chunk_size and current_chunk:
                chunks.append(" ".join(current_chunk))

                # Start new chunk with overlap (last 2 sentences)
                overlap_sentences = (
                    current_chunk[-2:] if len(current_chunk) >= 2 else current_chunk
                )
                current_chunk = overlap_sentences + [sentence]
                current_length = sum(len(s) for s in current_chunk)
            else:
                current_chunk.append(sentence)
                current_length += sentence_length

        # Add the last chunk if any sentences remain
        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks

    def process_document(self, chat_id: int, image_b64: str) -> Tuple[str, int]:
        """Complete document processing pipeline.

        Pipeline steps:
        1. Extract all information from image using LLM
        2. Chunk the extracted text into overlapping segments
        3. Create embeddings for each chunk
        4. Store chunks with embeddings in database

        Args:
            chat_id: ID of the chat session this document belongs to
            image_b64: Base64-encoded image of the document

        Returns:
            Tuple of (extracted_text, chunk_count)

        Raises:
            DocumentProcessingException: If any step in the pipeline fails
        """
        try:
            # Step 1: Extract information
            logger.info(f"Extracting information for chat {chat_id}...")
            extracted_text = self.extract_information_from_image(image_b64)
            logger.info(f"Extracted {len(extracted_text)} characters from document")

            # Step 2: Chunk the text
            logger.info("Chunking extracted text...")
            chunks = self.chunk_text(extracted_text)
            logger.info(f"Created {len(chunks)} chunks")

            # Step 3 & 4: Create embeddings and store
            logger.info("Creating embeddings and storing contexts...")
            for idx, chunk in enumerate(chunks):
                # Create embedding for this chunk
                embedding = self.ollama_service.call_ollama_embed(chunk)

                # Store in database
                self.chat_service.add_context_chunk(
                    chat_id=chat_id, content=chunk, embedding=embedding, chunk_index=idx
                )
                logger.debug(f"Stored chunk {idx + 1}/{len(chunks)}")

            logger.info(f"Document processing complete for chat {chat_id}")
            return extracted_text, len(chunks)

        except Exception as e:
            logger.error(
                f"Document processing failed for chat {chat_id}: {e}", exc_info=True
            )
            raise DocumentProcessingException(filename=f"chat_{chat_id}", reason=str(e))
