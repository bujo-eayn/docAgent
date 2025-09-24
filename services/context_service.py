# services/context_service.py
from services.ollama_service import OllamaService
from app.faiss_indexer import build_index, search_index


class ContextService:
    def __init__(self):
        self.ollama_service = OllamaService()

    def build_context_from_prompt(self, prompt: str) -> str:
        """Build context using FAISS search based on user prompt"""
        try:
            query_vec = self.ollama_service.call_ollama_embed(prompt)
            index, ids_with_caps = build_index()

            if index is not None and ids_with_caps is not None:
                neighbors = search_index(
                    index, ids_with_caps, query_vec, top_k=2)
                if neighbors:
                    return "\n".join([
                        f"- {n['caption']}"
                        for n in neighbors
                        if n.get("caption")
                    ])
        except Exception:
            pass

        return ""
