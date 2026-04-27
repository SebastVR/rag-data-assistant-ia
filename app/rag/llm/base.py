from __future__ import annotations

from abc import ABC, abstractmethod


# ────────────────────────────────────────────────────────────────
class BaseLLMClient(ABC):
    @abstractmethod
    def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        """Genera una respuesta de texto a partir del prompt."""
