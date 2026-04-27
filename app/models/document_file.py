from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from app.db.base import Base


class DocumentFile(Base):
    """Archivo de documento asociado a un documento extraído."""

    # ─────────────────────────────────────────────────────────────
    __tablename__ = "document_files"

    id = Column(Integer, primary_key=True, autoincrement=True)
    scraped_document_id = Column(
        Integer, ForeignKey("scraped_documents.id"), nullable=False
    )
    file_url = Column(Text, nullable=False)
    file_type = Column(String, nullable=False)
    file_path = Column(Text)
    content_hash = Column(String, unique=True)
    title = Column(Text, unique=True)
    summary = Column(Text)
    status = Column(
        String, nullable=False, comment="pending, raw_saved, processed, failed"
    )
    error_message = Column(Text)
    processed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), nullable=False)
