from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List


# ────────────────────────────────────────────────────────────────
class BaseEmbeddingClient(ABC):
    @abstractmethod
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Genera embeddings para una lista de textos."""

    @abstractmethod
    def embedding_dimension(self) -> int:
        """Retorna el tamaño del vector de embedding."""
