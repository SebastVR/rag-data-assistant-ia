from __future__ import annotations

import requests

from app.rag.llm.base import BaseLLMClient


class OllamaClient(BaseLLMClient):
    """Cliente para interactuar con modelos Ollama."""

    # ─────────────────────────────────────────────────────────────
    def __init__(self, base_url: str, model: str, timeout: int = 120):
        """Inicializa el cliente con la URL base, modelo y timeout."""
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    # ─────────────────────────────────────────────────────────────
    def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        """Genera una respuesta usando el modelo Ollama."""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }
        if system_prompt:
            payload["system"] = system_prompt

        response = requests.post(
            f"{self.base_url}/api/generate",
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("response", "")
