# services/context_service.py - Updated for Chat-Based Context
from services.ollama_service import OllamaService
from services.chat_service import ChatService


class ContextService:
    def __init__(self):
        self.ollama_service = OllamaService()
        self.chat_service = ChatService()

    def build_context_from_query(self, chat_id: int, query: str, top_k: int = 3) -> str:
        """
        Build context from the chat's document by searching relevant chunks.
        Context is scoped to the specific chat only.
        """
        try:
            # Convert query to embedding
            query_vec = self.ollama_service.call_ollama_embed(query)

            # Search for relevant contexts within this chat only
            relevant_contexts = self.chat_service.search_context(
                chat_id, query_vec, top_k=top_k)

            if relevant_contexts:
                # Format context with similarity scores
                context_parts = []
                for ctx in relevant_contexts:
                    context_parts.append(
                        f"[Relevance: {ctx['similarity']:.2f}]\n{ctx['content']}"
                    )
                return "\n\n---\n\n".join(context_parts)
        except Exception as e:
            print(f"Error building context: {e}")

        return ""