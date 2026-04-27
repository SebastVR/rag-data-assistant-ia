from __future__ import annotations

from typing import List

from sentence_transformers import SentenceTransformer

from app.rag.embeddings.base import BaseEmbeddingClient


# ────────────────────────────────────────────────────────────────
class SentenceTransformerEmbeddingClient(BaseEmbeddingClient):
    """Cliente de embeddings usando SentenceTransformer."""

    # ────────────────────────────────────────────────────────────────
    def __init__(self, model_name: str):
        """Inicializa el modelo de embeddings con el nombre dado."""
        self._model = SentenceTransformer(model_name)

    # ────────────────────────────────────────────────────────────────
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Genera embeddings para una lista de textos."""
        if not texts:
            return []
        vectors = self._model.encode(texts, normalize_embeddings=True)
        return vectors.tolist()

    # ────────────────────────────────────────────────────────────────
    def embedding_dimension(self) -> int:
        """Retorna el tamaño del vector de embedding del modelo."""
        return int(self._model.get_sentence_embedding_dimension())
