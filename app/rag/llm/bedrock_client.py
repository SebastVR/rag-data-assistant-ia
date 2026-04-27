from __future__ import annotations

from botocore.config import Config

from app.config.settings import settings
from app.rag.llm.base import BaseLLMClient


class BedrockClient(BaseLLMClient):
    """Cliente para interactuar con modelos Bedrock de AWS."""

    # ─────────────────────────────────────────────────────────────
    def __init__(self, model_id: str):
        """Inicializa el cliente con el ID del modelo."""
        self.model_id = model_id

    # ─────────────────────────────────────────────────────────────
    def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        """Genera una respuesta usando el modelo Bedrock."""
        try:
            import boto3
        except ImportError as exc:
            raise RuntimeError("boto3 package is not installed") from exc

        client = boto3.client(
            "bedrock-runtime",
            region_name=settings.aws_region_name,
            aws_access_key_id=settings.aws_s3_access_key_id,
            aws_secret_access_key=settings.aws_s3_secret_access_key,
            config=Config(
                retries={"max_attempts": 3, "mode": "standard"},
                connect_timeout=3,
                read_timeout=120,
            ),
        )

        payload: dict = {
            "modelId": self.model_id,
            "messages": [{"role": "user", "content": [{"text": prompt}]}],
            "inferenceConfig": {
                "maxTokens": settings.bedrock_max_new_tokens,
                "temperature": settings.bedrock_temperature,
            },
        }

        if system_prompt:
            payload["system"] = [{"text": system_prompt}]

        response = client.converse(**payload)
        content = response.get("output", {}).get("message", {}).get("content", [])

        for part in content:
            text = part.get("text")
            if text:
                return text

        return ""
