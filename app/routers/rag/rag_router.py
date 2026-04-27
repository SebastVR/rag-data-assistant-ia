import time
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from sqlalchemy import func

from app.celery_worker.tasks import (
    process_pdf_file_task,
    process_pending_ingestion_task,
    vectorize_html_document_task,
)
from app.config.settings import settings
from app.db.db_connection import SessionLocal
from app.models.conversation import Conversation
from app.models.document_file import DocumentFile
from app.models.message import Message
from app.rag.analytics.vector_metrics import get_vectorization_totals
from app.services.llm.runtime_config_service import get_runtime_llm_config
from app.services.llm.usage_logging_service import create_llm_usage_log
from app.services.rag.rag_query_service import RagQueryService
from app.util.responses import StandardStreamingResponse

try:
    from app.controllers.analytics.analytics_controller import get_recent_conversations
except ImportError:
    get_recent_conversations = None


from app.schemas.rag import (
    ConversationCreateRequest,
    ConversationCreateResponse,
    RagChatRequest,
    RagQuestionRequest,
)

router = APIRouter(prefix="/api/v1/rag", tags=["rag"])


# ─────────────────────────────────────────────────────────────
@router.post("/conversations", response_model=ConversationCreateResponse)
def create_conversation(request: ConversationCreateRequest):
    """Crea una nueva conversación vacía."""
    db = SessionLocal()
    try:
        session_id = request.session_id or str(uuid4())
        now = datetime.now(timezone.utc)
        title = request.title or "Chat"
        row = Conversation(
            session_id=session_id,
            title=title,
            channel="api",
            created_at=now,
            updated_at=now,
        )
        db.add(row)
        db.flush()
        db.refresh(row)
        return ConversationCreateResponse(
            id=row.id,
            session_id=row.session_id,
            title=row.title,
            channel=row.channel,
            created_at=row.created_at.isoformat(),
            updated_at=row.updated_at.isoformat(),
        )
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────
@router.get("/embeddings")
def get_embeddings_info():
    """Devuelve información real de los embeddings vectorizados."""
    db = SessionLocal()
    try:
        vector_metrics = get_vectorization_totals(db)
        return {
            "embedding_model": settings.rag_embedding_model,
            "vector_dim": 384,  # Puedes parametrizar esto si lo tienes en settings
            "vectorized_documents": vector_metrics.get("vectorized_documents", 0),
            "vectorized_pdf_documents": vector_metrics.get(
                "vectorized_pdf_documents", 0
            ),
            "vectorized_chunks": vector_metrics.get("vectorized_chunks", 0),
        }
    finally:
        db.close()


# --- Ejemplo de función generadora para chat streaming ---
def chat_stream_response(question: str):
    # Aquí deberías usar tu lógica real de streaming LLM
    # Este es un ejemplo simple que simula chunks
    import time

    for chunk in [
        f"Procesando pregunta: {question}",
        "\nChunk 1...",
        "\nChunk 2...",
        "\nRespuesta final.",
    ]:
        yield chunk
        time.sleep(0.5)


# ─────────────────────────────────────────────────────────────
@router.post("/chat/streaming")
async def chat_streaming_endpoint(request: RagQuestionRequest):
    """Endpoint de chat en streaming (respuesta por chunks)."""
    return StandardStreamingResponse(chat_stream_response(request.question))


def _resolve_or_create_conversation(db, payload: RagChatRequest) -> Conversation:
    if payload.conversation_id is not None:
        row = db.get(Conversation, payload.conversation_id)
        if row is None:
            raise ValueError(f"conversation_id={payload.conversation_id} no existe")
        return row

    if payload.session_id:
        row = (
            db.query(Conversation)
            .filter(Conversation.session_id == payload.session_id)
            .first()
        )
        if row is not None:
            return row

    session_id = payload.session_id or str(uuid4())
    now = datetime.now(timezone.utc)
    row = Conversation(
        session_id=session_id,
        title=(payload.question[:80] if payload.question else "Chat"),
        channel="api",
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.flush()
    return row


def _next_message_order(db, conversation_id: int) -> int:
    max_order = (
        db.query(func.max(Message.message_order))
        .filter(Message.conversation_id == conversation_id)
        .scalar()
    )
    return int(max_order or 0)


def _history_as_text(db, conversation_id: int, history_messages: int) -> str:
    if history_messages <= 0:
        return ""

    rows = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.message_order.desc())
        .limit(history_messages)
        .all()
    )
    if not rows:
        return ""

    rows.reverse()
    lines = []
    for msg in rows:
        role = (msg.role or "user").strip().lower()
        role_label = "Usuario" if role == "user" else "Asistente"
        lines.append(f"{role_label}: {msg.content}")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────
@router.post("/ingestion/pending")
def trigger_pending_ingestion(limit: int = 20):
    """Lanza la tarea de ingesta pendiente."""
    task = process_pending_ingestion_task.delay(limit=limit)
    return {
        "message": "Pending ingestion task dispatched",
        "task_id": task.id,
        "limit": limit,
    }


# ─────────────────────────────────────────────────────────────
@router.post("/ingestion/files/{document_file_id}")
def trigger_pdf_ingestion(document_file_id: int):
    """Lanza la tarea de ingesta de PDF."""
    task = process_pdf_file_task.delay(document_file_id=document_file_id)
    return {
        "message": "PDF ingestion task dispatched",
        "task_id": task.id,
        "document_file_id": document_file_id,
    }


# ─────────────────────────────────────────────────────────────
@router.post("/ingestion/html/{scraped_document_id}")
def trigger_html_ingestion(scraped_document_id: int):
    """Lanza la tarea de ingesta de HTML scrapeado."""
    task = vectorize_html_document_task.delay(scraped_document_id=scraped_document_id)
    return {
        "message": "HTML ingestion task dispatched",
        "task_id": task.id,
        "scraped_document_id": scraped_document_id,
    }


# ─────────────────────────────────────────────────────────────
@router.post("/query")
def rag_query(request: RagQuestionRequest):
    """Realiza una consulta RAG simple (sin historial)."""
    started = time.perf_counter()
    db = SessionLocal()
    active_provider = settings.llm_provider.lower()
    active_model = settings.llm_model_name
    try:
        runtime = get_runtime_llm_config(db)
        active_provider = runtime.get("llm_provider", settings.llm_provider).lower()
        active_model = runtime.get("llm_model_name", settings.llm_model_name)
        active_model_path = runtime.get("llm_model_path", settings.llm_model_path)

        service = RagQueryService(
            llm_provider=active_provider,
            llm_model_name=active_model,
            llm_model_path=active_model_path,
        )
        result = service.answer(
            question=request.question,
            use_rerank=request.use_rerank,
        )
        latency_ms = int((time.perf_counter() - started) * 1000)
        usage = create_llm_usage_log(
            db=db,
            provider=active_provider,
            model_name=active_model,
            prompt_text=request.question,
            response_text=str(result.get("answer") or ""),
            status="success",
            latency_ms=latency_ms,
        )
        result["llm_usage_log_id"] = usage.id
        return result
    except Exception as exc:
        latency_ms = int((time.perf_counter() - started) * 1000)
        create_llm_usage_log(
            db=db,
            provider=active_provider,
            model_name=active_model,
            prompt_text=request.question,
            response_text="",
            status="failed",
            latency_ms=latency_ms,
            error_message=str(exc),
        )
        raise
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────
@router.post("/ask")
def rag_ask(request: RagQuestionRequest):
    """Alias explícito para inferencia RAG sin historial conversacional."""
    return rag_query(request)


# ─────────────────────────────────────────────────────────────
@router.post("/chat")
def rag_chat(request: RagChatRequest):
    """Realiza un chat RAG con historial conversacional."""
    started = time.perf_counter()
    db = SessionLocal()
    active_provider = settings.llm_provider.lower()
    active_model = settings.llm_model_name
    conversation = None
    user_message = None

    try:
        runtime = get_runtime_llm_config(db)
        active_provider = runtime.get("llm_provider", settings.llm_provider).lower()
        active_model = runtime.get("llm_model_name", settings.llm_model_name)
        active_model_path = runtime.get("llm_model_path", settings.llm_model_path)

        conversation = _resolve_or_create_conversation(db, request)
        history_text = _history_as_text(
            db,
            conversation_id=conversation.id,
            history_messages=request.history_messages,
        )

        next_order = _next_message_order(db, conversation.id)
        user_message = Message(
            conversation_id=conversation.id,
            role="user",
            content=request.question,
            message_order=next_order + 1,
            created_at=datetime.now(timezone.utc),
        )
        db.add(user_message)
        db.flush()

        service = RagQueryService(
            llm_provider=active_provider,
            llm_model_name=active_model,
            llm_model_path=active_model_path,
        )
        result = service.answer(
            question=request.question,
            use_rerank=request.use_rerank,
            conversation_history=history_text,
        )

        assistant_message = Message(
            conversation_id=conversation.id,
            role="assistant",
            content=str(result.get("answer") or ""),
            message_order=next_order + 2,
            created_at=datetime.now(timezone.utc),
        )
        conversation.updated_at = datetime.now(timezone.utc)
        db.add(assistant_message)
        db.flush()

        latency_ms = int((time.perf_counter() - started) * 1000)
        usage = create_llm_usage_log(
            db=db,
            provider=active_provider,
            model_name=active_model,
            prompt_text=request.question,
            response_text=str(result.get("answer") or ""),
            status="success",
            message_id=assistant_message.id,
            conversation_id=conversation.id,
            latency_ms=latency_ms,
        )

        return {
            "conversation_id": conversation.id,
            "session_id": conversation.session_id,
            "history_messages_used": request.history_messages,
            "llm_usage_log_id": usage.id,
            **result,
        }
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        db.rollback()
        latency_ms = int((time.perf_counter() - started) * 1000)
        if conversation is not None:
            # Solo loguea el message_id si el mensaje existe y fue insertado exitosamente
            safe_message_id = (
                user_message.id
                if (
                    user_message
                    and user_message.id
                    and db.get(Message, user_message.id)
                )
                else None
            )
            create_llm_usage_log(
                db=db,
                provider=active_provider,
                model_name=active_model,
                prompt_text=request.question,
                response_text="",
                status="failed",
                message_id=safe_message_id,
                conversation_id=conversation.id,
                latency_ms=latency_ms,
                error_message=str(exc),
            )
        raise
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────
@router.get("/chat/{conversation_id}/messages")
def rag_chat_messages(conversation_id: int, limit: int = 50, offset: int = 0):
    """Obtiene los mensajes de una conversación específica."""
    db = SessionLocal()
    try:
        conversation = db.get(Conversation, conversation_id)
        if conversation is None:
            return {
                "conversation_id": conversation_id,
                "total": 0,
                "items": [],
            }

        total = (
            db.query(Message).filter(Message.conversation_id == conversation_id).count()
        )
        rows = (
            db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.message_order.asc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        return {
            "conversation_id": conversation_id,
            "session_id": conversation.session_id,
            "total": total,
            "limit": limit,
            "offset": offset,
            "items": [
                {
                    "id": row.id,
                    "role": row.role,
                    "content": row.content,
                    "message_order": row.message_order,
                    "created_at": row.created_at,
                }
                for row in rows
            ],
        }
    finally:
        db.close()


# --- Celery/status: Consultar estado de procesamiento de PDF ---


# ─────────────────────────────────────────────────────────────
@router.get("/status/files/{document_file_id}")
def get_pdf_file_status(document_file_id: int):
    """Consulta el estado de procesamiento de un archivo PDF."""
    db = SessionLocal()
    try:
        file_row = db.get(DocumentFile, document_file_id)
        if not file_row:
            return {"status": "not_found", "document_file_id": document_file_id}
        return {
            "document_file_id": file_row.id,
            "status": file_row.status,
            "error_message": file_row.error_message,
            "summary": file_row.summary,
            "file_path": file_row.file_path,
            "processed_at": file_row.processed_at,
        }
    finally:
        db.close()


# --- NUEVO: Listar conversaciones activas ---
@router.get("/conversations")
def list_conversations(limit: int = 50, offset: int = 0, q: str = None):
    """
    Devuelve la lista de conversaciones activas para mostrar en el frontend.
    """
    db = SessionLocal()
    try:
        # Si existe función reutilizable de analytics, úsala
        if get_recent_conversations:
            items = get_recent_conversations(db=db, limit=limit, q=q)
            total = len(items)
            return {
                "total": total,
                "limit": limit,
                "offset": offset,
                "items": items[offset : offset + limit],
            }

        # Si no, implementa aquí
        query = db.query(Conversation)
        if q:
            term = f"%{q.strip()}%"
            query = query.filter(
                (Conversation.title.ilike(term)) | (Conversation.session_id.ilike(term))
            )
        total = query.count()
        rows = (
            query.order_by(Conversation.updated_at.desc(), Conversation.id.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        # Obtener métricas de mensajes
        conversation_ids = [row.id for row in rows]
        metrics_rows = (
            db.query(
                Message.conversation_id.label("conversation_id"),
                func.count(Message.id).label("message_count"),
                func.max(Message.created_at).label("last_message_at"),
            )
            .filter(Message.conversation_id.in_(conversation_ids))
            .group_by(Message.conversation_id)
            .all()
        )
        metrics = {
            row.conversation_id: {
                "message_count": int(row.message_count or 0),
                "last_message_at": (
                    row.last_message_at.isoformat() if row.last_message_at else None
                ),
            }
            for row in metrics_rows
        }
        items = []
        for row in rows:
            item_metrics = metrics.get(row.id, {})
            items.append(
                {
                    "id": int(row.id),
                    "session_id": row.session_id,
                    "title": row.title or "Chat",
                    "channel": row.channel,
                    "created_at": (
                        row.created_at.isoformat() if row.created_at else None
                    ),
                    "updated_at": (
                        row.updated_at.isoformat() if row.updated_at else None
                    ),
                    "message_count": int(item_metrics.get("message_count", 0)),
                    "last_message_at": item_metrics.get("last_message_at"),
                }
            )
        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "items": items,
        }
    finally:
        db.close()
