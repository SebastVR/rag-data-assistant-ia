from fastapi import APIRouter

from app.rag.reranker.text_reranker import simple_text_rerank
from app.schemas.rerank import RerankRequest, RerankResult

router = APIRouter(prefix="/api/v1/rerank", tags=["rerank"])


# ─────────────────────────────────────────────────────────────
@router.post("/text", response_model=list[RerankResult])
def rerank_text_endpoint(request: RerankRequest):
    """
    Rerank de textos usando coincidencia de palabras (similitud simple).
    """
    return simple_text_rerank(request.query, request.texts, request.limit)
