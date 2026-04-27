from __future__ import annotations

from app.rag.llm.base import BaseLLMClient


class LlamaCppClient(BaseLLMClient):
    """Cliente para interactuar con modelos Llama.cpp."""

    # ─────────────────────────────────────────────────────────────
    def __init__(self, model_path: str, n_ctx: int = 4096, n_threads: int = 4):
        """Inicializa el cliente con la ruta del modelo y configuración."""
        try:
            from llama_cpp import Llama
        except ImportError as exc:
            raise RuntimeError("llama-cpp-python package is not installed") from exc

        self._llm = Llama(
            model_path=model_path,
            n_ctx=n_ctx,
            n_threads=n_threads,
        )

    # ─────────────────────────────────────────────────────────────
    def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        """Genera una respuesta usando el modelo Llama.cpp."""
        final_prompt = prompt
        if system_prompt:
            final_prompt = f"[SYSTEM]\n{system_prompt}\n\n[USER]\n{prompt}"

        output = self._llm(
            final_prompt,
            max_tokens=512,
            stop=["</s>"],
        )
        choices = output.get("choices", [])
        if not choices:
            return ""
        return choices[0].get("text", "").strip()
