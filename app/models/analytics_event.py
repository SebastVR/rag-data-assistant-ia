from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String

from app.db.base import Base


class AnalyticsEvent(Base):
    """Evento de analítica registrado en la base de datos."""

    # ─────────────────────────────────────────────────────────────
    __tablename__ = "analytics_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"))
    message_id = Column(Integer, ForeignKey("messages.id"))
    event_type = Column(String, nullable=False)
    event_payload = Column(JSON)
    created_at = Column(DateTime(timezone=True), nullable=False)
