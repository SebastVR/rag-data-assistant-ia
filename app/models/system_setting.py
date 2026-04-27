from sqlalchemy import Column, DateTime, Integer, String, Text

from app.db.base import Base


class SystemSetting(Base):
    """Configuración del sistema almacenada en la base de datos."""

    # ─────────────────────────────────────────────────────────────
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String, unique=True, nullable=False)
    value = Column(Text, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)
