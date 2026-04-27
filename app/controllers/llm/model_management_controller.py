from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.models.language_model import LanguageModel
from app.services.llm.runtime_config_service import set_runtime_llm_config
from app.services.s3_storage import S3Storage

MODEL_FOLDER = "models/llm"


# ─────────────────────────────────────────────────────────────
def _ensure_session(db: Any) -> Session:
    """Verifica que el objeto db sea una sesión de SQLAlchemy."""
    if not isinstance(db, Session):
        raise TypeError("Este endpoint solo soporta SQLAlchemy Session (APP_ENV=dev)")
    return db


# ─────────────────────────────────────────────────────────────
def _sanitize_filename(value: str) -> str:
    """Sanitiza el nombre de archivo para almacenamiento seguro."""
    return re.sub(r"[^a-zA-Z0-9._-]", "_", value)


# ─────────────────────────────────────────────────────────────
def upload_llm_model(
    db: Any,
    *,
    file_name: str,
    file_bytes: bytes,
    provider: str,
    model_name: str,
    input_token_cost: Decimal,
    output_token_cost: Decimal,
    set_as_active: bool,
) -> dict[str, Any]:
    """Sube un modelo LLM a S3 y lo registra en la base de datos."""
    session = _ensure_session(db)
    now = datetime.now(timezone.utc)

    safe_name = _sanitize_filename(file_name)
    object_name = f"{int(now.timestamp())}_{safe_name}"

    storage = S3Storage()
    storage_path = storage.write_file(MODEL_FOLDER, object_name, file_bytes)
    model_s3_path = f"s3://{storage.bucket_name}/{storage_path}"

    row = (
        session.query(LanguageModel)
        .filter(
            LanguageModel.provider == provider,
            LanguageModel.name == model_name,
        )
        .first()
    )

    if row is None:
        row = LanguageModel(
            name=model_name,
            provider=provider,
            input_token_cost=input_token_cost,
            output_token_cost=output_token_cost,
            max_tokens=8192,
            description=f"Uploaded model file: {os.path.basename(storage_path)}",
            created_at=now,
            updated_at=now,
        )
        session.add(row)
    else:
        row.input_token_cost = input_token_cost
        row.output_token_cost = output_token_cost
        row.updated_at = now
        row.description = f"Uploaded model file: {os.path.basename(storage_path)}"

    session.commit()

    if set_as_active:
        set_runtime_llm_config(
            session,
            llm_provider=provider,
            llm_model_name=model_name,
            llm_model_path=model_s3_path,
        )

    return {
        "provider": provider,
        "model_name": model_name,
        "model_path": model_s3_path,
        "set_as_active": set_as_active,
    }


# ─────────────────────────────────────────────────────────────
def _resolve_llama_model_path_from_registry(
    session: Session,
    *,
    provider: str,
    model_name: str,
) -> str:
    """Resuelve la ruta S3 de un modelo llama_cpp registrado."""
    row = (
        session.query(LanguageModel)
        .filter(
            LanguageModel.provider == provider,
            LanguageModel.name == model_name,
        )
        .first()
    )
    if row is None or not row.description:
        raise RuntimeError(
            "No existe metadata de upload para este modelo llama_cpp. "
            "Pasa model_path o vuelve a subir el .gguf."
        )

    marker = "Uploaded model file: "
    if marker not in row.description:
        raise RuntimeError(
            "No se pudo inferir model_path desde LanguageModel.description"
        )

    filename = row.description.split(marker, 1)[1].strip()
    if not filename:
        raise RuntimeError("Filename de modelo vacio en LanguageModel.description")

    storage = S3Storage()
    return f"s3://{storage.bucket_name}/{MODEL_FOLDER}/{filename}"


# ─────────────────────────────────────────────────────────────
def activate_llm_model(
    db: Any,
    *,
    provider: str,
    model_name: str,
    model_path: str | None = None,
    set_as_active: bool = True,
) -> dict[str, Any]:
    """Activa un modelo LLM registrado y lo configura como activo si se indica."""
    session = _ensure_session(db)
    normalized_provider = provider.strip().lower()
    resolved_model_name = model_name.strip()

    if not resolved_model_name:
        raise RuntimeError("model_name es requerido")

    existing_model = (
        session.query(LanguageModel)
        .filter(
            LanguageModel.provider == normalized_provider,
            LanguageModel.name == resolved_model_name,
        )
        .first()
    )

    if existing_model is None:
        raise RuntimeError(
            "El modelo/provider no existe en LanguageModel. "
            "Registra o sube el modelo primero."
        )

    resolved_model_path = model_path or ""
    if normalized_provider == "llama_cpp":
        resolved_model_path = resolved_model_path.strip() if resolved_model_path else ""
        if not resolved_model_path:
            resolved_model_path = _resolve_llama_model_path_from_registry(
                session,
                provider=normalized_provider,
                model_name=resolved_model_name,
            )

    if set_as_active:
        set_runtime_llm_config(
            session,
            llm_provider=normalized_provider,
            llm_model_name=resolved_model_name,
            llm_model_path=resolved_model_path,
        )

    return {
        "provider": normalized_provider,
        "model_name": resolved_model_name,
        "model_path": resolved_model_path,
        "set_as_active": set_as_active,
    }


# ─────────────────────────────────────────────────────────────
def list_llm_model_options(
    db: Any,
    *,
    provider: str | None = None,
) -> dict[str, Any]:
    """Lista las opciones de modelos LLM disponibles por proveedor."""
    session = _ensure_session(db)

    query = session.query(LanguageModel)
    normalized_provider = (provider or "").strip().lower()
    if normalized_provider:
        query = query.filter(LanguageModel.provider == normalized_provider)

    rows = query.order_by(LanguageModel.provider.asc(), LanguageModel.name.asc()).all()

    providers: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        providers.setdefault(row.provider, []).append(
            {
                "id": row.id,
                "model_name": row.name,
                "provider": row.provider,
                "description": row.description,
                "max_tokens": row.max_tokens,
            }
        )

    return {
        "total_models": len(rows),
        "providers": providers,
    }


# ─────────────────────────────────────────────────────────────
def activate_llm_model_by_id(
    db: Any,
    *,
    language_model_id: int,
    set_as_active: bool = True,
) -> dict[str, Any]:
    """Activa un modelo LLM por su ID en la base de datos."""
    session = _ensure_session(db)
    row = session.get(LanguageModel, language_model_id)
    if row is None:
        raise RuntimeError(f"language_model_id={language_model_id} no existe")

    return activate_llm_model(
        session,
        provider=row.provider,
        model_name=row.name,
        model_path=None,
        set_as_active=set_as_active,
    )
