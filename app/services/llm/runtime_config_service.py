from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.config.settings import settings
from app.models.system_setting import SystemSetting


# ────────────────────────────────────────────────────────────────
def get_runtime_llm_config(db: Session) -> dict[str, str]:
    """Obtiene la configuración LLM activa desde la base de datos o settings."""
    config = {
        "llm_provider": settings.llm_provider,
        "llm_model_name": settings.llm_model_name,
        "llm_model_path": settings.llm_model_path,
    }

    rows = (
        db.query(SystemSetting)
        .filter(
            SystemSetting.key.in_(["llm_provider", "llm_model_name", "llm_model_path"])
        )
        .all()
    )
    for row in rows:
        config[row.key] = row.value

    return config


# ────────────────────────────────────────────────────────────────
def set_runtime_llm_config(
    db: Session,
    *,
    llm_provider: str,
    llm_model_name: str,
    llm_model_path: str,
) -> None:
    """Actualiza la configuración LLM activa en la base de datos."""
    now = datetime.now(timezone.utc)
    payload = {
        "llm_provider": llm_provider,
        "llm_model_name": llm_model_name,
        "llm_model_path": llm_model_path,
    }

    for key, value in payload.items():
        row = db.query(SystemSetting).filter(SystemSetting.key == key).first()
        if row is None:
            db.add(
                SystemSetting(
                    key=key,
                    value=value,
                    description="Runtime LLM configuration",
                    created_at=now,
                    updated_at=now,
                )
            )
            continue

        row.value = value
        row.updated_at = now

    db.commit()
