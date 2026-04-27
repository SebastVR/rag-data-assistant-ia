from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship

from app.db.base import Base


class LLMUsageLog(Base):
    """Registro de uso de modelos LLM en la base de datos."""

    # ─────────────────────────────────────────────────────────────
    __tablename__ = "llm_usage_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(Integer, ForeignKey("messages.id"))
    conversation_id = Column(Integer, ForeignKey("conversations.id"))
    provider = Column(String, nullable=False)
    model = Column(String, nullable=False)
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    input_cost = Column(Numeric, default=0)
    output_cost = Column(Numeric, default=0)
    total_cost = Column(Numeric, default=0)
    latency_ms = Column(Integer)
    status = Column(String, nullable=False)
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), nullable=False)

    message = relationship("Message", back_populates="llm_usage_logs")
