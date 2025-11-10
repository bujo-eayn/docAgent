# services/context_service.py - Updated for Chat-Based Context
"""Context service for retrieving relevant document context.

This service orchestrates the context retrieval process:
1. Convert user query to embedding
2. Search for relevant context chunks in the chat's document
3. Format and return the context for the LLM
"""
from typing import Optional

from config import config
from services.chat_service import ChatService
from services.ollama_service import OllamaService
from utils.logger import setup_logger

logger = setup_logger(__name__)


class ContextService:
    """Service for building context from user queries."""

    def __init__(self):
        """Initialize context service with required dependencies."""
        self.ollama_service = OllamaService()
        self.chat_service = ChatService()

    def build_context_from_query(
        self, chat_id: int, query: str, top_k: Optional[int] = None
    ) -> str:
        """Build context from the chat's document by searching relevant chunks.

        Context is scoped to the specific chat only - searches only within
        that chat's document chunks.

        Args:
            chat_id: ID of the chat to search within
            query: User's question or query text
            top_k: Number of relevant contexts to retrieve (default: from config)

        Returns:
            Formatted context string with relevance scores,
            or empty string if no context found or error occurs
        """
        top_k = top_k or config.top_k_contexts

        try:
            # Convert query to embedding
            query_vec = self.ollama_service.call_ollama_embed(query)

            # Search for relevant contexts within this chat only
            relevant_contexts = self.chat_service.search_context(
                chat_id, query_vec, top_k=top_k
            )

            if relevant_contexts:
                # Format context with similarity scores
                context_parts = []
                for ctx in relevant_contexts:
                    context_parts.append(
                        f"[Relevance: {ctx['similarity']:.2f}]\n{ctx['content']}"
                    )
                return "\n\n---\n\n".join(context_parts)

        except Exception as e:
            logger.error(
                f"Error building context for chat {chat_id}: {e}", exc_info=True
            )

        return ""
