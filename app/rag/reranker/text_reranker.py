from typing import List, Optional

from app.schemas.rerank import RerankResult


# ─────────────────────────────────────────────────────────────
def simple_text_rerank(
    query: str, texts: List[str], limit: Optional[int] = None
) -> List[RerankResult]:
    """
    Rerank de textos usando coincidencia de substring (similitud simple).
    Devuelve los textos ordenados por score descendente.
    """
    scored = []
    for i, text in enumerate(texts):
        # Score: proporción de palabras del query presentes en el texto
        query_words = set(query.lower().split())
        text_words = set(text.lower().split())
        score = len(query_words & text_words) / max(1, len(query_words))
        scored.append(RerankResult(text=text, score=score, index=i, rank=0))
    # Ordenar por score descendente
    sorted_results = sorted(scored, key=lambda x: x.score, reverse=True)
    for rank, item in enumerate(sorted_results):
        item.rank = rank
    if limit is not None and limit < len(sorted_results):
        sorted_results = sorted_results[:limit]
    return sorted_results
