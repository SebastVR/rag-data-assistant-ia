from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.language_model import LanguageModel
from app.models.llm_usage_log import LLMUsageLog


# ────────────────────────────────────────────────────────────────
def _normalize_provider(provider: str) -> str:
    """Normaliza el nombre del proveedor LLM para uso interno."""
    value = (provider or "").strip().lower()
    aliases = {
        "openai": "chatgpt",
        "bedrock": "claude",
    }
    return aliases.get(value, value)


# ────────────────────────────────────────────────────────────────
def _estimate_tokens(text: str) -> int:
    """Estima la cantidad de tokens en un texto dado."""
    cleaned = (text or "").strip()
    if not cleaned:
        return 0
    words = len(cleaned.split())
    return max(1, int(words * 1.3))


# ────────────────────────────────────────────────────────────────
def _compute_cost(tokens: int, per_token_cost: Decimal | int | float | None) -> Decimal:
    """Calcula el costo total dado el número de tokens y el costo por token."""
    if not per_token_cost:
        return Decimal("0")
    return (Decimal(tokens) * Decimal(str(per_token_cost))).quantize(
        Decimal("0.000001")
    )


# ────────────────────────────────────────────────────────────────
def _resolve_model_costs(
    db: Session,
    provider: str,
    model_name: str,
) -> tuple[Decimal, Decimal]:
    """Obtiene el costo por token de entrada y salida para un modelo dado."""
    normalized_provider = _normalize_provider(provider)
    row = (
        db.query(LanguageModel)
        .filter(
            LanguageModel.provider == normalized_provider,
            LanguageModel.name == model_name,
        )
        .first()
    )

    if row is None:
        row = (
            db.query(LanguageModel)
            .filter(LanguageModel.provider == normalized_provider)
            .first()
        )

    if row is None:
        return Decimal("0"), Decimal("0")

    return Decimal(str(row.input_token_cost or 0)), Decimal(
        str(row.output_token_cost or 0)
    )


# ────────────────────────────────────────────────────────────────
def create_llm_usage_log(
    db: Session,
    *,
    provider: str,
    model_name: str,
    prompt_text: str,
    response_text: str,
    status: str,
    message_id: int | None = None,
    conversation_id: int | None = None,
    latency_ms: int | None = None,
    error_message: str | None = None,
) -> LLMUsageLog:
    """Crea y guarda un registro de uso de LLM en la base de datos."""
    input_tokens = _estimate_tokens(prompt_text)
    output_tokens = _estimate_tokens(response_text)
    total_tokens = input_tokens + output_tokens
    normalized_provider = _normalize_provider(provider)

    input_price, output_price = _resolve_model_costs(
        db=db,
        provider=provider,
        model_name=model_name,
    )

    input_cost = _compute_cost(input_tokens, input_price)
    output_cost = _compute_cost(output_tokens, output_price)

    row = LLMUsageLog(
        message_id=message_id,
        conversation_id=conversation_id,
        provider=normalized_provider,
        model=model_name,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        input_cost=input_cost,
        output_cost=output_cost,
        total_cost=(input_cost + output_cost),
        latency_ms=latency_ms,
        status=status,
        error_message=error_message,
        created_at=datetime.now(timezone.utc),
    )

    db.add(row)
    db.commit()
    db.refresh(row)
    return row
