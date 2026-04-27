import json
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.document_chunk import DocumentChunk
from app.models.document_section import DocumentSection
from app.models.language_model import LanguageModel
from app.models.llm_usage_log import LLMUsageLog
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
def _to_decimal_str(value: Any) -> str:
    """Convierte un valor Decimal a string decimal plano."""
    if isinstance(value, Decimal):
        return format(value, "f")
    return str(value or 0)


# ─────────────────────────────────────────────────────────────
def _parse_json(value: Any) -> dict[str, Any]:
    """Parsea un string JSON o dict a un diccionario de Python."""
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


# ─────────────────────────────────────────────────────────────
def list_language_models(
    db: Any,
    provider: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
) -> dict[str, Any]:
    """Lista los modelos de lenguaje registrados con filtros y paginación."""
    session = _ensure_session(db)
    query = session.query(LanguageModel)

    if provider:
        query = query.filter(LanguageModel.provider == provider)

    if q:
        q_like = f"%{q.strip()}%"
        query = query.filter(
            or_(
                LanguageModel.name.ilike(q_like),
                LanguageModel.provider.ilike(q_like),
                LanguageModel.description.ilike(q_like),
            )
        )

    total = query.count()
    rows = (
        query.order_by(LanguageModel.provider.asc(), LanguageModel.name.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [
            {
                "id": row.id,
                "name": row.name,
                "provider": row.provider,
                "input_token_cost": _to_decimal_str(row.input_token_cost),
                "output_token_cost": _to_decimal_str(row.output_token_cost),
                "max_tokens": row.max_tokens,
                "description": row.description,
                "created_at": _to_iso(row.created_at),
                "updated_at": _to_iso(row.updated_at),
            }
            for row in rows
        ],
    }


# ─────────────────────────────────────────────────────────────
def list_document_sections(
    db: Any,
    scraped_document_id: Optional[int] = None,
    doc_id: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
) -> dict[str, Any]:
    """Lista las secciones de documentos extraídos con filtros y paginación."""
    session = _ensure_session(db)

    query = session.query(
        DocumentSection,
        ScrapedDocument.doc_id,
        ScrapedDocument.title,
    ).join(
        ScrapedDocument,
        DocumentSection.scraped_document_id == ScrapedDocument.id,
    )

    if scraped_document_id is not None:
        query = query.filter(DocumentSection.scraped_document_id == scraped_document_id)

    if doc_id:
        query = query.filter(ScrapedDocument.doc_id == doc_id)

    total = query.count()
    rows = query.order_by(DocumentSection.id.desc()).offset(offset).limit(limit).all()

    items = []
    for section, parent_doc_id, parent_title in rows:
        items.append(
            {
                "id": section.id,
                "scraped_document_id": section.scraped_document_id,
                "doc_id": parent_doc_id,
                "document_title": parent_title,
                "heading": section.heading,
                "content": section.content,
                "position": section.position,
                "created_at": _to_iso(section.created_at),
            }
        )

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": items,
    }


# ─────────────────────────────────────────────────────────────
def list_document_chunks(
    db: Any,
    scraped_document_id: Optional[int] = None,
    doc_id: Optional[str] = None,
    source_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
) -> dict[str, Any]:
    """Lista los fragmentos de documentos extraídos con filtros y paginación."""
    session = _ensure_session(db)

    query = session.query(
        DocumentChunk,
        ScrapedDocument.doc_id,
        ScrapedDocument.title,
    ).join(
        ScrapedDocument,
        DocumentChunk.scraped_document_id == ScrapedDocument.id,
    )

    if scraped_document_id is not None:
        query = query.filter(DocumentChunk.scraped_document_id == scraped_document_id)

    if doc_id:
        query = query.filter(ScrapedDocument.doc_id == doc_id)

    if status:
        query = query.filter(DocumentChunk.status == status)

    if source_type:
        query = query.filter(
            DocumentChunk.chunk_metadata["source_type"].astext == source_type
        )

    total = query.count()
    rows = query.order_by(DocumentChunk.id.desc()).offset(offset).limit(limit).all()

    items = []
    for chunk, parent_doc_id, parent_title in rows:
        items.append(
            {
                "id": chunk.id,
                "scraped_document_id": chunk.scraped_document_id,
                "doc_id": parent_doc_id,
                "document_title": parent_title,
                "chunk_id": chunk.chunk_id,
                "chunk_index": chunk.chunk_index,
                "content": chunk.content,
                "token_count": chunk.token_count,
                "qdrant_collection": chunk.qdrant_collection,
                "qdrant_point_id": chunk.qdrant_point_id,
                "embedding_model": chunk.embedding_model,
                "chunk_metadata": _parse_json(chunk.chunk_metadata),
                "status": chunk.status,
                "error_message": chunk.error_message,
                "created_at": _to_iso(chunk.created_at),
            }
        )

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": items,
    }


# ─────────────────────────────────────────────────────────────
def list_llm_usage_logs(
    db: Any,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    conversation_id: Optional[int] = None,
    message_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
) -> dict[str, Any]:
    """Lista los registros de uso de LLMs con filtros y paginación."""
    session = _ensure_session(db)
    query = session.query(LLMUsageLog)

    if provider:
        query = query.filter(LLMUsageLog.provider == provider)
    if model:
        query = query.filter(LLMUsageLog.model == model)
    if conversation_id is not None:
        query = query.filter(LLMUsageLog.conversation_id == conversation_id)
    if message_id is not None:
        query = query.filter(LLMUsageLog.message_id == message_id)
    if status:
        query = query.filter(LLMUsageLog.status == status)

    total = query.count()
    rows = query.order_by(LLMUsageLog.id.desc()).offset(offset).limit(limit).all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [
            {
                "id": row.id,
                "message_id": row.message_id,
                "conversation_id": row.conversation_id,
                "provider": row.provider,
                "model": row.model,
                "input_tokens": row.input_tokens,
                "output_tokens": row.output_tokens,
                "total_tokens": row.total_tokens,
                "input_cost": _to_decimal_str(row.input_cost),
                "output_cost": _to_decimal_str(row.output_cost),
                "total_cost": _to_decimal_str(row.total_cost),
                "latency_ms": row.latency_ms,
                "status": row.status,
                "error_message": row.error_message,
                "created_at": _to_iso(row.created_at),
            }
            for row in rows
        ],
    }


# ─────────────────────────────────────────────────────────────
def list_chunk_scraped_document_ids(db: Any) -> dict[str, Any]:
    """Lista los IDs de documentos extraídos con cantidad de chunks y última fecha."""
    session = _ensure_session(db)

    rows = (
        session.query(
            DocumentChunk.scraped_document_id,
            func.count(DocumentChunk.id).label("chunks_count"),
            func.max(DocumentChunk.created_at).label("last_chunk_created_at"),
            ScrapedDocument.doc_id,
            ScrapedDocument.title,
        )
        .join(
            ScrapedDocument,
            DocumentChunk.scraped_document_id == ScrapedDocument.id,
        )
        .group_by(
            DocumentChunk.scraped_document_id,
            ScrapedDocument.doc_id,
            ScrapedDocument.title,
        )
        .order_by(DocumentChunk.scraped_document_id.asc())
        .all()
    )

    return {
        "total_scraped_document_ids": len(rows),
        "items": [
            {
                "scraped_document_id": row.scraped_document_id,
                "doc_id": row.doc_id,
                "document_title": row.title,
                "chunks_count": int(row.chunks_count or 0),
                "last_chunk_created_at": _to_iso(row.last_chunk_created_at),
            }
            for row in rows
        ],
    }
