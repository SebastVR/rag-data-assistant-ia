from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.controllers.db.models_controller import (
    list_chunk_scraped_document_ids,
    list_document_chunks,
    list_document_sections,
    list_language_models,
    list_llm_usage_logs,
)
from app.db.db_connection import get_db

router = APIRouter(prefix="/api/v1/db/models", tags=["db:models"])


# ─────────────────────────────────────────────────────────────
@router.get("/language-models")
def get_language_models(
    provider: Optional[str] = Query(default=None),
    q: Optional[str] = Query(default=None, min_length=1),
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db=Depends(get_db),
):
    """Lista los modelos de lenguaje disponibles."""
    try:
        return list_language_models(
            db=db,
            provider=provider,
            q=q,
            limit=limit,
            offset=offset,
        )
    except TypeError as e:
        raise HTTPException(status_code=501, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────
@router.get("/document-sections")
def get_document_sections(
    scraped_document_id: Optional[int] = Query(default=None, ge=1),
    doc_id: Optional[str] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db=Depends(get_db),
):
    """Lista las secciones de documentos."""
    try:
        return list_document_sections(
            db=db,
            scraped_document_id=scraped_document_id,
            doc_id=doc_id,
            limit=limit,
            offset=offset,
        )
    except TypeError as e:
        raise HTTPException(status_code=501, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────
@router.get("/document-chunks")
def get_document_chunks(
    scraped_document_id: Optional[int] = Query(default=None, ge=1),
    doc_id: Optional[str] = Query(default=None),
    source_type: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db=Depends(get_db),
):
    """Lista los fragmentos (chunks) de documentos."""
    try:
        return list_document_chunks(
            db=db,
            scraped_document_id=scraped_document_id,
            doc_id=doc_id,
            source_type=source_type,
            status=status,
            limit=limit,
            offset=offset,
        )
    except TypeError as e:
        raise HTTPException(status_code=501, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────
@router.get("/document-chunks/scraped-document-ids")
def get_chunk_scraped_document_ids(db=Depends(get_db)):
    """Lista los IDs de documentos scrapeados con chunks."""
    try:
        return list_chunk_scraped_document_ids(db=db)
    except TypeError as e:
        raise HTTPException(status_code=501, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────
@router.get("/llm-usage-logs")
def get_llm_usage_logs(
    provider: Optional[str] = Query(default=None),
    model: Optional[str] = Query(default=None),
    conversation_id: Optional[int] = Query(default=None, ge=1),
    message_id: Optional[int] = Query(default=None, ge=1),
    status: Optional[str] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db=Depends(get_db),
):
    """Lista los logs de uso de modelos LLM."""
    try:
        return list_llm_usage_logs(
            db=db,
            provider=provider,
            model=model,
            conversation_id=conversation_id,
            message_id=message_id,
            status=status,
            limit=limit,
            offset=offset,
        )
    except TypeError as e:
        raise HTTPException(status_code=501, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
