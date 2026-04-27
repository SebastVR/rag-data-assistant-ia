from sqlalchemy import Column, DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import relationship

from app.db.base import Base


class DocumentSection(Base):
    """Sección de un documento extraído."""

    # ─────────────────────────────────────────────────────────────
    __tablename__ = "document_sections"

    id = Column(Integer, primary_key=True, autoincrement=True)
    scraped_document_id = Column(
        Integer, ForeignKey("scraped_documents.id"), nullable=False
    )
    heading = Column(Text)
    content = Column(Text, nullable=False)
    position = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)

    scraped_document = relationship("ScrapedDocument", back_populates="sections")
