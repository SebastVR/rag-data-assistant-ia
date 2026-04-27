from sqlalchemy import Column, DateTime, Integer, Numeric, String

from app.db.base import Base


class LanguageModel(Base):
    """Modelo de lenguaje registrado en la base de datos."""

    # ─────────────────────────────────────────────────────────────
    __tablename__ = "language_models"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)
    provider = Column(String, nullable=False)
    input_token_cost = Column(Numeric, default=0)
    output_token_cost = Column(Numeric, default=0)
    max_tokens = Column(Integer)
    description = Column(String)
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)
