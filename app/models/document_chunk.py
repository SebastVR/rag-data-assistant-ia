from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.base import Base


class DocumentChunk(Base):
    """Fragmento de documento almacenado en la base de datos."""

    # ─────────────────────────────────────────────────────────────
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    scraped_document_id = Column(
        Integer, ForeignKey("scraped_documents.id"), nullable=False
    )
    chunk_id = Column(String, unique=True, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    token_count = Column(Integer)
    qdrant_collection = Column(String)
    qdrant_point_id = Column(String, unique=True)
    embedding_model = Column(String, nullable=False)
    chunk_metadata = Column(JSON)
    status = Column(String, nullable=False, comment="pending, vectorized, failed")
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), nullable=False)

    scraped_document = relationship("ScrapedDocument", back_populates="chunks")
