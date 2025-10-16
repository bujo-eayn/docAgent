# services/document_processor.py - Document Processing Service
import re
from typing import Dict, List

import requests

from services.chat_service import ChatService
from services.ollama_service import OllamaService


class DocumentProcessor:
    """Service to handle document processing: extraction, chunking, embedding, and storage."""
    def __init__(self):
        self.ollama_service = OllamaService()
        self.chat_service = ChatService()

    def extract_information_from_image(self, image_b64: str) -> str:
        """
        Extract ALL information from the uploaded image using Ollama.
        Returns comprehensive text extraction.
        """
        system_prompt = """You are a document information extraction expert. Your task is to extract ALL information from the provided image.

Extract and describe:
1. All visible text (headings, labels, values, legends, annotations)
2. All data points and their values
3. Chart/graph types and what they represent
4. Relationships between data elements
5. Any trends, patterns, or insights visible
6. Color coding, symbols, and their meanings
7. Axes, scales, units of measurement
8. Any formulas, equations, or calculations shown
9. Contextual information (titles, dates, sources)

Be exhaustive and detailed. Structure your extraction in clear sections."""

        url = f"{self.ollama_service.base_url}/api/chat"
        payload = {
            "model": self.ollama_service.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "Extract all information from this image.",
                    "images": [image_b64]},
            ],
            "stream": False  # Non-streaming for extraction
        }

        response = requests.post(url, json=payload, timeout=360)
        response.raise_for_status()

        result = response.json()
        message = result.get("message", {})
        content = message.get("content", "")

        return content

    def chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """
        Split extracted text into overlapping chunks for better context retrieval.
        """
        # Split by sentences
        sentences = re.split(r'(?<=[.!?])\s+', text)

        chunks = []
        current_chunk = []
        current_length = 0

        for sentence in sentences:
            sentence_length = len(sentence)

            if current_length + sentence_length > chunk_size and current_chunk:
                # Save current chunk
                chunks.append(' '.join(current_chunk))

                # Start new chunk with overlap
                overlap_sentences = current_chunk[-2:] if len(
                    current_chunk) >= 2 else current_chunk
                current_chunk = overlap_sentences + [sentence]
                current_length = sum(len(s) for s in current_chunk)
            else:
                current_chunk.append(sentence)
                current_length += sentence_length

        # Add the last chunk
        if current_chunk:
            chunks.append(' '.join(current_chunk))

        return chunks

    def process_document(self, chat_id: int, image_b64: str):
        """
        Complete document processing pipeline:
        1. Extract all information from image
        2. Chunk the extracted text
        3. Create embeddings for each chunk
        4. Store in database with chat_id
        """
        # Step 1: Extract information
        print(f"Extracting information for chat {chat_id}...")
        extracted_text = self.extract_information_from_image(image_b64)

        # Step 2: Chunk the text
        print(f"Chunking extracted text...")
        chunks = self.chunk_text(extracted_text, chunk_size=500, overlap=50)
        print(f"Created {len(chunks)} chunks")

        # Step 3 & 4: Create embeddings and store
        print(f"Creating embeddings and storing contexts...")
        for idx, chunk in enumerate(chunks):
            # Create embedding for this chunk
            embedding = self.ollama_service.call_ollama_embed(chunk)

            # Store in database
            self.chat_service.add_context_chunk(
                chat_id=chat_id,
                content=chunk,
                embedding=embedding,
                chunk_index=idx
            )
            print(f"  ✓ Stored chunk {idx + 1}/{len(chunks)}")

        print(f"✅ Document processing complete for chat {chat_id}")
        return extracted_text, len(chunks)
