from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Sequence


class BaseVectorStore(ABC):
    @abstractmethod
    def upsert(self, ids: Sequence[str], vectors: Sequence[List[float]], payloads: Sequence[Dict[str, object]]) -> None:
        """Insert or update vectors in the store."""

    @abstractmethod
    def search(self, query_vector: List[float], limit: int, filter_payload: Dict[str, object] | None = None):
        """Search vectors by similarity."""
