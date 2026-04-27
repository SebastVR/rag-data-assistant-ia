import json
from typing import Any, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.document_file import DocumentFile
from app.models.scraped_document import ScrapedDocument


# ─────────────────────────────────────────────────────────────
def _ensure_session(db: Any) -> Session:
    """Verifica que el objeto db sea una sesión de SQLAlchemy."""
    if not isinstance(db, Session):
        raise TypeError("Este endpoint solo soporta SQLAlchemy Session (APP_ENV=dev)")
    return db


# ─────────────────────────────────────────────────────────────
def _to_iso(value: Any) -> Optional[str]:
    """Convierte un valor datetime a string ISO 8601."""
    return value.isoformat() if value is not None else None


# ─────────────────────────────────────────────────────────────
def _parse_headings(raw_headings: Any) -> list[str]:
    """Parsea los headings de un documento (list o JSON string)."""
    if raw_headings is None:
        return []
    if isinstance(raw_headings, list):
        return raw_headings
    if isinstance(raw_headings, str):
        try:
            parsed = json.loads(raw_headings)
            return parsed if isinstance(parsed, list) else []
        except json.JSONDecodeError:
            return []
    return []


# ─────────────────────────────────────────────────────────────
def list_scraped_documents(
    db: Any,
    limit: int = 20,
    offset: int = 0,
    q: Optional[str] = None,
    status: Optional[str] = None,
) -> dict[str, Any]:
    """Lista los documentos extraídos con filtros y paginación."""
    session = _ensure_session(db)

    query = session.query(ScrapedDocument)

    if status:
        query = query.filter(ScrapedDocument.status == status)

    if q:
        q_like = f"%{q.strip()}%"
        query = query.filter(
            or_(
                ScrapedDocument.doc_id.ilike(q_like),
                ScrapedDocument.title.ilike(q_like),
                ScrapedDocument.final_url.ilike(q_like),
                ScrapedDocument.text.ilike(q_like),
            )
        )

    total = query.count()
    docs = query.order_by(ScrapedDocument.id.desc()).offset(offset).limit(limit).all()

    items = []
    for doc in docs:
        items.append(
            {
                "id": doc.id,
                "scraping_run_id": doc.scraping_run_id,
                "doc_id": doc.doc_id,
                "source_name": doc.source_name,
                "url": doc.url,
                "final_url": doc.final_url,
                "title": doc.title,
                "category": doc.category,
                "headings": _parse_headings(doc.headings),
                "text": doc.text,
                "raw_file_path": doc.raw_file_path,
                "processed_file_path": doc.processed_file_path,
                "content_hash": doc.content_hash,
                "status": doc.status,
                "error_message": doc.error_message,
                "scraped_at": _to_iso(doc.scraped_at),
                "created_at": _to_iso(doc.created_at),
            }
        )

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": items,
    }


# ─────────────────────────────────────────────────────────────
def get_scraped_document_detail(db: Any, doc_id: str) -> dict[str, Any]:
    """Obtiene el detalle de un documento extraído, incluyendo sus archivos."""
    session = _ensure_session(db)

    doc = (
        session.query(ScrapedDocument).filter(ScrapedDocument.doc_id == doc_id).first()
    )
    if not doc:
        raise KeyError(f"No existe el documento con doc_id={doc_id}")

    files = (
        session.query(DocumentFile)
        .filter(DocumentFile.scraped_document_id == doc.id)
        .order_by(DocumentFile.id.desc())
        .all()
    )

    return {
        "id": doc.id,
        "doc_id": doc.doc_id,
        "source_name": doc.source_name,
        "url": doc.url,
        "source_url": doc.final_url,
        "title": doc.title,
        "category": doc.category,
        "headings": _parse_headings(doc.headings),
        "text": doc.text,
        "status": doc.status,
        "error_message": doc.error_message,
        "scraped_at": _to_iso(doc.scraped_at),
        "created_at": _to_iso(doc.created_at),
        "files": [
            {
                "id": item.id,
                "file_url": item.file_url,
                "file_type": item.file_type,
                "file_path": item.file_path,
                "title": item.title,
                "summary": item.summary,
                "status": item.status,
                "error_message": item.error_message,
                "processed_at": _to_iso(item.processed_at),
                "created_at": _to_iso(item.created_at),
            }
            for item in files
        ],
    }


# ─────────────────────────────────────────────────────────────
def list_document_files(
    db: Any,
    file_type: Optional[str] = "pdf",
    status: Optional[str] = None,
    doc_id: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
) -> dict[str, Any]:
    """Lista los archivos de documentos con filtros y paginación."""
    session = _ensure_session(db)

    query = session.query(
        DocumentFile,
        ScrapedDocument.doc_id,
        ScrapedDocument.final_url,
    ).join(
        ScrapedDocument,
        DocumentFile.scraped_document_id == ScrapedDocument.id,
    )

    if file_type:
        query = query.filter(DocumentFile.file_type == file_type)

    if status:
        query = query.filter(DocumentFile.status == status)

    if doc_id:
        query = query.filter(ScrapedDocument.doc_id == doc_id)

    total = query.count()
    rows = query.order_by(DocumentFile.id.desc()).offset(offset).limit(limit).all()

    items = []
    for file_row, parent_doc_id, source_url in rows:
        items.append(
            {
                "id": file_row.id,
                "scraped_document_id": file_row.scraped_document_id,
                "doc_id": parent_doc_id,
                "source_url": source_url,
                "file_url": file_row.file_url,
                "file_type": file_row.file_type,
                "file_path": file_row.file_path,
                "title": file_row.title,
                "summary": file_row.summary,
                "status": file_row.status,
                "error_message": file_row.error_message,
                "processed_at": _to_iso(file_row.processed_at),
                "created_at": _to_iso(file_row.created_at),
            }
        )

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": items,
    }
