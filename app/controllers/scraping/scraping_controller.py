import json
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from app.config.settings import settings
from app.scraping.crawler import crawl_and_save
from app.services.s3_storage import S3Storage
from app.services.scraping.html_processing_service import (
    process_all_html_and_return_json,
)

PROCESSED_FOLDER = "bbva_json"
PROCESSED_FILE = "html_docs_unicos.json"


# ─────────────────────────────────────────────────────────────
def process_scraped_html(allowed_domain: str) -> Dict[str, Any]:
    """Procesa los HTMLs bajo el prefijo correspondiente al dominio en S3."""
    prefix = _domain_to_prefix(allowed_domain)
    docs = process_all_html_and_return_json(prefix)
    return {
        "total_docs": len(docs),
        "output_key": f"{prefix.replace('_html', '_json')}/html_docs_unicos.json",
    }


# ─────────────────────────────────────────────────────────────
def run_crawl(
    base_url: Optional[str] = None,
    allowed_domain: Optional[str] = None,
    max_pages: Optional[int] = None,
    timeout: Optional[int] = None,
) -> Dict[str, Any]:
    """Ejecuta el proceso de crawling y guarda los resultados en S3."""
    start_url = (base_url or settings.scraper_base_url).strip()
    domain = (allowed_domain or settings.scraper_allowed_domain).strip().lower()
    pages = max_pages or settings.scraper_max_pages
    request_timeout = timeout or settings.scraper_timeout

    parsed = urlparse(start_url)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError("base_url no es una URL valida")

    if domain not in parsed.netloc.lower():
        raise ValueError("allowed_domain debe coincidir con el dominio de base_url")

    prefix = _domain_to_prefix(domain)
    return crawl_and_save(
        start_url=start_url,
        base_domain=domain,
        max_pages=pages,
        timeout=request_timeout,
        user_agent=settings.scraper_user_agent,
        s3_folder=prefix,
    )


# ─────────────────────────────────────────────────────────────
def _domain_to_prefix(domain: str) -> str:
    """Convierte un dominio (e.g., bbva.com.co) en un prefijo S3 (e.g., bbva_html)."""
    name = domain.split(".")[0].lower()
    return f"{name}_html"


# ─────────────────────────────────────────────────────────────
def _load_processed_docs(allowed_domain: str) -> Dict[str, Any]:
    """Carga los documentos procesados desde S3 para un dominio dado."""
    prefix = _domain_to_prefix(allowed_domain).replace("_html", "_json")
    s3 = S3Storage()
    content = s3.read_file(prefix, PROCESSED_FILE)
    return json.loads(content.decode("utf-8"))


# ─────────────────────────────────────────────────────────────
def list_processed_documents(
    allowed_domain: str,
    limit: int = 20,
    offset: int = 0,
    q: Optional[str] = None,
) -> Dict[str, Any]:
    """Lista los documentos procesados de un dominio, con filtros y paginación."""
    docs = _load_processed_docs(allowed_domain)
    items: List[tuple[str, Dict[str, Any]]] = list(docs.items())

    if q:
        q_norm = q.lower().strip()
        items = [
            (doc_id, doc)
            for doc_id, doc in items
            if q_norm in (doc.get("title") or "").lower()
            or q_norm in (doc.get("text") or "").lower()
            or q_norm in (doc.get("source_url") or "").lower()
        ]

    total = len(items)
    paginated = items[offset : offset + limit]

    summaries = []
    for doc_id, doc in paginated:
        text = doc.get("text") or ""
        summaries.append(
            {
                "doc_id": doc_id,
                "file": doc.get("file"),
                "title": doc.get("title"),
                "headings": doc.get("headings", [])[:5],
                "source_url": doc.get("source_url"),
                "text_preview": text[:400],
                "text_length": len(text),
            }
        )

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": summaries,
    }


# ─────────────────────────────────────────────────────────────
def get_processed_document(doc_id: str, allowed_domain: str) -> Dict[str, Any]:
    """Obtiene el detalle de un documento procesado por su ID y dominio."""
    docs = _load_processed_docs(allowed_domain)
    if doc_id not in docs:
        raise KeyError(f"No existe el documento con id {doc_id}")
    return {"doc_id": doc_id, **docs[doc_id]}
