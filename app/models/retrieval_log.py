from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.db.base import Base


class RetrievalLog(Base):
    """Registro de recuperación de fragmentos de documentos."""

    # ─────────────────────────────────────────────────────────────
    __tablename__ = "retrieval_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=False)
    chunk_id = Column(String, ForeignKey("document_chunks.chunk_id"), nullable=False)
    source_url = Column(Text)
    source_title = Column(Text)
    retrieval_score = Column(Float)
    rerank_score = Column(Float)
    rank_position = Column(Integer)
    used_in_context = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False)

    message = relationship("Message", back_populates="retrieval_logs")
