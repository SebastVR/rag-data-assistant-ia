from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.base import Base


class ScrapedDocument(Base):
    """Documento extraído y procesado por el sistema."""

    # ─────────────────────────────────────────────────────────────
    __tablename__ = "scraped_documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    scraping_run_id = Column(Integer, ForeignKey("scraping_runs.id"), nullable=False)
    doc_id = Column(String, unique=True, nullable=False)
    source_name = Column(String, nullable=False)
    url = Column(Text, nullable=False)
    final_url = Column(Text)
    title = Column(Text)
    category = Column(String)
    headings = Column(Text)  # JSON stringified list of headings
    text = Column(Text, nullable=False)  # Cleaned text for vectorization
    raw_file_path = Column(Text, nullable=False)
    processed_file_path = Column(Text)
    content_hash = Column(String, unique=True)
    status = Column(
        String, nullable=False, comment="raw_saved, processed, failed, vectorized"
    )
    error_message = Column(Text)
    scraped_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)

    scraping_run = relationship("ScrapingRun", back_populates="documents")
    sections = relationship("DocumentSection", back_populates="scraped_document")
    chunks = relationship("DocumentChunk", back_populates="scraped_document")
