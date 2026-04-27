from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func

from app.models.conversation import Conversation
from app.models.llm_usage_log import LLMUsageLog
from app.models.message import Message
from app.rag.analytics import get_vectorization_totals


# ─────────────────────────────────────────────────────────────
def _window_start(days: int) -> datetime:
    """Calcula la fecha de inicio de la ventana de días para KPIs."""
    safe_days = max(1, int(days))
    now = datetime.now(timezone.utc)
    return now - timedelta(days=safe_days)


# ─────────────────────────────────────────────────────────────
def get_analytics_kpis(db, *, days: int = 30) -> dict:
    """Obtiene los KPIs de analítica para la ventana de días indicada."""
    start = _window_start(days)

    total_conversations = db.query(func.count(Conversation.id)).scalar() or 0
    total_messages = db.query(func.count(Message.id)).scalar() or 0

    llm_calls_window = (
        db.query(func.count(LLMUsageLog.id))
        .filter(LLMUsageLog.created_at >= start)
        .scalar()
        or 0
    )

    total_cost_window = (
        db.query(func.coalesce(func.sum(LLMUsageLog.total_cost), 0))
        .filter(LLMUsageLog.created_at >= start)
        .scalar()
        or 0
    )

    avg_latency_ms_window = (
        db.query(func.coalesce(func.avg(LLMUsageLog.latency_ms), 0))
        .filter(LLMUsageLog.created_at >= start)
        .scalar()
        or 0
    )

    vector_metrics = get_vectorization_totals(db)

    return {
        "window_days": int(days),
        "total_conversations": int(total_conversations),
        "total_messages": int(total_messages),
        "llm_calls_window": int(llm_calls_window),
        "total_cost_window": float(total_cost_window),
        "avg_latency_ms_window": float(avg_latency_ms_window),
        **vector_metrics,
    }


# ─────────────────────────────────────────────────────────────
def get_analytics_daily_cost(db, *, days: int = 30) -> list[dict]:
    """Obtiene el costo diario de uso de LLMs para la ventana de días indicada."""
    start = _window_start(days)

    rows = (
        db.query(
            func.date(LLMUsageLog.created_at).label("day"),
            func.coalesce(func.sum(LLMUsageLog.total_cost), 0).label("total_cost"),
            func.coalesce(func.sum(LLMUsageLog.total_tokens), 0).label("total_tokens"),
            func.count(LLMUsageLog.id).label("calls"),
        )
        .filter(LLMUsageLog.created_at >= start)
        .group_by(func.date(LLMUsageLog.created_at))
        .order_by(func.date(LLMUsageLog.created_at).asc())
        .all()
    )

    return [
        {
            "day": str(row.day),
            "total_cost": float(row.total_cost or 0),
            "total_tokens": int(row.total_tokens or 0),
            "calls": int(row.calls or 0),
        }
        for row in rows
    ]


# ─────────────────────────────────────────────────────────────
def get_analytics_daily_latency(db, *, days: int = 30) -> list[dict]:
    """Obtiene la latencia diaria promedio y máxima de LLMs para la ventana de días indicada."""
    start = _window_start(days)

    rows = (
        db.query(
            func.date(LLMUsageLog.created_at).label("day"),
            func.coalesce(func.avg(LLMUsageLog.latency_ms), 0).label("avg_latency_ms"),
            func.coalesce(func.max(LLMUsageLog.latency_ms), 0).label("max_latency_ms"),
            func.count(LLMUsageLog.id).label("calls"),
        )
        .filter(LLMUsageLog.created_at >= start)
        .group_by(func.date(LLMUsageLog.created_at))
        .order_by(func.date(LLMUsageLog.created_at).asc())
        .all()
    )

    return [
        {
            "day": str(row.day),
            "avg_latency_ms": float(row.avg_latency_ms or 0),
            "max_latency_ms": int(row.max_latency_ms or 0),
            "calls": int(row.calls or 0),
        }
        for row in rows
    ]


# ─────────────────────────────────────────────────────────────
def get_analytics_cost_breakdown(db, *, days: int = 30) -> list[dict]:
    """Obtiene el desglose de costos por modelo y proveedor de LLMs para la ventana de días indicada."""
    start = _window_start(days)

    rows = (
        db.query(
            LLMUsageLog.provider.label("provider"),
            LLMUsageLog.model.label("model"),
            func.coalesce(func.sum(LLMUsageLog.total_cost), 0).label("total_cost"),
            func.coalesce(func.sum(LLMUsageLog.total_tokens), 0).label("total_tokens"),
            func.count(LLMUsageLog.id).label("calls"),
        )
        .filter(LLMUsageLog.created_at >= start)
        .group_by(LLMUsageLog.provider, LLMUsageLog.model)
        .order_by(func.sum(LLMUsageLog.total_cost).desc())
        .all()
    )

    return [
        {
            "provider": str(row.provider or "unknown"),
            "model": str(row.model or "unknown"),
            "total_cost": float(row.total_cost or 0),
            "total_tokens": int(row.total_tokens or 0),
            "calls": int(row.calls or 0),
        }
        for row in rows
    ]


# ─────────────────────────────────────────────────────────────
def get_recent_conversations(
    db, *, limit: int = 30, q: str | None = None
) -> list[dict]:
    """Obtiene las conversaciones recientes con métricas básicas."""
    safe_limit = max(1, min(int(limit), 100))
    query = db.query(Conversation)

    if q:
        term = f"%{q.strip()}%"
        query = query.filter(
            (Conversation.title.ilike(term)) | (Conversation.session_id.ilike(term))
        )

    conversations = (
        query.order_by(Conversation.updated_at.desc(), Conversation.id.desc())
        .limit(safe_limit)
        .all()
    )

    if not conversations:
        return []

    conversation_ids = [row.id for row in conversations]

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

    items: list[dict] = []
    for row in conversations:
        item_metrics = metrics.get(row.id, {})
        items.append(
            {
                "id": int(row.id),
                "session_id": row.session_id,
                "title": row.title or "Chat",
                "channel": row.channel,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "updated_at": row.updated_at.isoformat() if row.updated_at else None,
                "message_count": int(item_metrics.get("message_count", 0)),
                "last_message_at": item_metrics.get("last_message_at"),
            }
        )

    return items
