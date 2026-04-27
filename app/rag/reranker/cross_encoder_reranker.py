from __future__ import annotations

from typing import List, Sequence, Tuple

from sentence_transformers import CrossEncoder


# ─────────────────────────────────────────────────────────────
class CrossEncoderReranker:
    """Reranker basado en CrossEncoder para ordenar textos según relevancia."""

    # ─────────────────────────────────────────────────────────────
    def __init__(self, model_name: str):
        """Inicializa el modelo CrossEncoder con el nombre dado."""
        self._model = CrossEncoder(model_name)

    # ─────────────────────────────────────────────────────────────
    def rerank(
        self, query: str, texts: Sequence[str], top_k: int
    ) -> List[Tuple[int, float]]:
        """Reordena los textos según relevancia para la consulta dada."""
        if not texts:
            return []

        pairs = [(query, text) for text in texts]
        scores = self._model.predict(pairs)
        indexed = list(enumerate(scores.tolist()))
        indexed.sort(key=lambda item: item[1], reverse=True)
        return indexed[:top_k]
