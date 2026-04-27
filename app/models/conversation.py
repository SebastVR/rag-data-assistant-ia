from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.orm import relationship

from app.db.base import Base


class Conversation(Base):
    """Conversación registrada en la base de datos."""

    # ─────────────────────────────────────────────────────────────
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, unique=True, nullable=False)
    title = Column(String)
    channel = Column(String)
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)

    messages = relationship("Message", back_populates="conversation")
