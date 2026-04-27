from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.language_model import LanguageModel


# ────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class LanguageModelSeed:
    name: str
    provider: str
    input_token_cost: Decimal
    output_token_cost: Decimal
    max_tokens: int
    description: str


DEFAULT_LANGUAGE_MODELS: tuple[LanguageModelSeed, ...] = (
    LanguageModelSeed(
        name="llama3.2",
        provider="ollama",
        input_token_cost=Decimal("2.5"),
        output_token_cost=Decimal("5.0"),
        max_tokens=8192,
        description="Default local model via Ollama",
    ),
    LanguageModelSeed(
        name="gpt-4o-mini",
        provider="chatgpt",
        input_token_cost=Decimal("12.0"),
        output_token_cost=Decimal("24.0"),
        max_tokens=128000,
        description="OpenAI ChatGPT low-cost model",
    ),
    LanguageModelSeed(
        name="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
        provider="claude",
        input_token_cost=Decimal("18.0"),
        output_token_cost=Decimal("36.0"),
        max_tokens=200000,
        description="Anthropic Claude Sonnet model via Bedrock",
    ),
)


# ────────────────────────────────────────────────────────────────
def ensure_default_language_models(db: Session) -> dict[str, int]:
    """Asegura que los modelos de lenguaje por defecto existan en la base de datos."""
    created = 0
    updated = 0
    now = datetime.now(timezone.utc)

    for item in DEFAULT_LANGUAGE_MODELS:
        row = (
            db.query(LanguageModel)
            .filter(
                LanguageModel.name == item.name,
                LanguageModel.provider == item.provider,
            )
            .first()
        )

        if row is None:
            db.add(
                LanguageModel(
                    name=item.name,
                    provider=item.provider,
                    input_token_cost=item.input_token_cost,
                    output_token_cost=item.output_token_cost,
                    max_tokens=item.max_tokens,
                    description=item.description,
                    created_at=now,
                    updated_at=now,
                )
            )
            created += 1
            continue

        dirty = False
        if row.input_token_cost != item.input_token_cost:
            row.input_token_cost = item.input_token_cost
            dirty = True
        if row.output_token_cost != item.output_token_cost:
            row.output_token_cost = item.output_token_cost
            dirty = True
        if row.max_tokens != item.max_tokens:
            row.max_tokens = item.max_tokens
            dirty = True
        if row.description != item.description:
            row.description = item.description
            dirty = True

        if dirty:
            row.updated_at = now
            updated += 1

    db.commit()
    return {"created": created, "updated": updated}
