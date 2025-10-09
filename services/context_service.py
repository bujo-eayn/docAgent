# services/context_service.py
from services.ollama_service import OllamaService
from services.database_service import DatabaseService


class ContextService:
    def __init__(self):
        self.ollama_service = OllamaService()
        self.db_service = DatabaseService()

    def build_context_from_prompt(self, prompt: str) -> str:
        """Build context using pgvector search based on user prompt"""
        try:
            # Convert prompt to embedding
            query_vec = self.ollama_service.call_ollama_embed(prompt)

            # Search for similar images using pgvector
            neighbors = self.db_service.search_similar_images(
                query_vec, top_k=2)

            if neighbors:
                # Format context from similar images
                context_parts = []
                for n in neighbors:
                    if n.get("caption"):
                        # Include similarity score in context
                        context_parts.append(
                            f"- (Similarity: {1 - n['distance']:.2f}) {n['caption']}"
                        )
                return "\n".join(context_parts)
        except Exception as e:
            print(f"Error building context: {e}")
            pass

        return ""
