from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.controllers.db.documents_controller import (
    get_scraped_document_detail,
    list_document_files,
    list_scraped_documents,
)
from app.db.db_connection import get_db
from app.schemas.document import ListResponse, ScrapedDocumentDetail

router = APIRouter(prefix="/api/v1/db/documents", tags=["db:documents"])


# ─────────────────────────────────────────────────────────────
@router.get("/scraped", response_model=ListResponse)
def get_scraped_documents(
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    q: Optional[str] = Query(default=None, min_length=1),
    status: Optional[str] = Query(default=None),
    db=Depends(get_db),
):
    """Lista los documentos scrapeados."""
    try:
        result = list_scraped_documents(
            db=db,
            limit=limit,
            offset=offset,
            q=q,
            status=status,
        )
        return ListResponse(**result)
    except TypeError as e:
        raise HTTPException(status_code=501, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────
@router.get("/scraped/{doc_id}", response_model=ScrapedDocumentDetail)
def get_scraped_document(
    doc_id: str,
    db=Depends(get_db),
):
    """Obtiene el detalle de un documento scrapeado."""
    try:
        result = get_scraped_document_detail(db=db, doc_id=doc_id)
        return ScrapedDocumentDetail(**result)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except TypeError as e:
        raise HTTPException(status_code=501, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────
@router.get("/files", response_model=ListResponse)
def get_document_files(
    file_type: Optional[str] = Query(default="pdf"),
    status: Optional[str] = Query(default=None),
    doc_id: Optional[str] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db=Depends(get_db),
):
    """Lista los archivos de documentos según filtros."""
    try:
        result = list_document_files(
            db=db,
            file_type=file_type,
            status=status,
            doc_id=doc_id,
            limit=limit,
            offset=offset,
        )
        return ListResponse(**result)
    except TypeError as e:
        raise HTTPException(status_code=501, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
