from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, Query

from app.controllers.scraping.scraping_controller import (
    get_processed_document,
    list_processed_documents,
    process_scraped_html,
    run_crawl,
)
from app.schemas.scraping import CrawlRequest

router = APIRouter(prefix="/api/v1/scraping", tags=["scraping"])


def extract_domain(url: str) -> str:
    netloc = urlparse(url).netloc
    if netloc.startswith("www."):
        netloc = netloc[4:]
    return netloc


# ─────────────────────────────────────────────────────────────
@router.post("/crawl")
def crawl_site(payload: CrawlRequest):
    """Inicia el crawling y guarda los HTMLs bajo el prefijo en S3."""
    try:
        if not payload.base_url:
            raise ValueError("base_url es requerido")
        allowed_domain = extract_domain(payload.base_url)
        return run_crawl(
            base_url=payload.base_url,
            allowed_domain=allowed_domain,
            max_pages=payload.max_pages,
            timeout=payload.timeout,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────
@router.post("/process")
def process_html_documents(
    allowed_domain: str = Query(..., description="Dominio a procesar, e.g. bbva.com.co")
):
    """Procesa los HTMLs scrapeados bajo el prefijo del dominio."""
    try:
        return process_scraped_html(allowed_domain=allowed_domain)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────
@router.get("/documents")
def get_processed_documents(
    allowed_domain: str = Query(
        ..., description="Dominio a consultar, e.g. bbva.com.co"
    ),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    q: str | None = Query(default=None, min_length=1),
):
    """Lista los documentos procesados para un dominio."""
    try:
        return list_processed_documents(
            allowed_domain=allowed_domain, limit=limit, offset=offset, q=q
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────
@router.get("/documents/{doc_id}")
def get_processed_document_by_id(
    doc_id: str,
    allowed_domain: str = Query(
        ..., description="Dominio a consultar, e.g. bbva.com.co"
    ),
):
    """Obtiene un documento procesado por su ID y dominio."""
    try:
        return get_processed_document(doc_id, allowed_domain=allowed_domain)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
