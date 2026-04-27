from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class ScrapingRun(Base):
    """Ejecución de scraping registrada en la base de datos."""

    # ─────────────────────────────────────────────────────────────
    __tablename__ = "scraping_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_name = Column(String, nullable=False)
    base_url = Column(Text, nullable=False)
    allowed_domain = Column(String, nullable=False)
    max_pages = Column(Integer, nullable=False)
    status = Column(String, nullable=False, comment="running, completed, failed")
    pages_found = Column(Integer, default=0)
    pages_processed = Column(Integer, default=0)
    pages_failed = Column(Integer, default=0)
    error_message = Column(Text)
    started_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    finished_at = Column(DateTime(timezone=True))
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    documents = relationship("ScrapedDocument", back_populates="scraping_run")
