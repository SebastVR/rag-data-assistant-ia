from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List

from app.config.settings import settings
from app.db.db_connection import SessionLocal
from app.rag.embeddings import SentenceTransformerEmbeddingClient
from app.rag.llm import BedrockClient, LlamaCppClient, OllamaClient, OpenAIClient
from app.rag.prompts import RAG_SYSTEM_PROMPT, RAG_USER_PROMPT_TEMPLATE
from app.rag.reranker import CrossEncoderReranker
from app.rag.vectorstore import QdrantVectorStore
from app.services.llm.runtime_config_service import get_runtime_llm_config
from app.services.s3_storage import S3Storage


# ────────────────────────────────────────────────────────────────
@dataclass
class RetrievalHit:
    score: float
    text: str
    metadata: dict


# ────────────────────────────────────────────────────────────────
class RagQueryService:
    """Servicio para consultas RAG: recuperación, reranking y generación de respuesta."""

    # ────────────────────────────────────────────────────────────────
    def __init__(
        self,
        *,
        llm_provider: str | None = None,
        llm_model_name: str | None = None,
        llm_model_path: str | None = None,
    ):
        """Inicializa los clientes de embeddings, vector store, reranker y LLM."""
        self.embedder = SentenceTransformerEmbeddingClient(settings.rag_embedding_model)
        self.vector_store = QdrantVectorStore(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
            grpc_port=settings.qdrant_grpc_port,
            collection_name=settings.qdrant_collection_name,
            vector_size=self.embedder.embedding_dimension(),
        )
        self.reranker = CrossEncoderReranker(settings.rag_reranker_model)
        self.llm_provider = llm_provider or settings.llm_provider
        self.llm_model_name = llm_model_name or settings.llm_model_name
        self.llm_model_path = llm_model_path or settings.llm_model_path

    # ────────────────────────────────────────────────────────────────
    @classmethod
    def from_runtime_config(cls) -> "RagQueryService":
        """Crea una instancia usando la configuración LLM activa en runtime."""
        db = SessionLocal()
        try:
            runtime = get_runtime_llm_config(db)
        finally:
            db.close()

        return cls(
            llm_provider=runtime.get("llm_provider"),
            llm_model_name=runtime.get("llm_model_name"),
            llm_model_path=runtime.get("llm_model_path"),
        )

    # ────────────────────────────────────────────────────────────────
    def retrieve(
        self, question: str, limit: int | None = None, use_rerank: bool = True
    ) -> List[RetrievalHit]:
        """Recupera los chunks más relevantes para una pregunta, con reranking opcional."""
        if limit is None:
            limit = settings.qdrant_max_chunks_retrieved

        query_vector = self.embedder.embed_texts([question])[0]
        points = self.vector_store.search(query_vector=query_vector, limit=limit)

        hits = [
            RetrievalHit(
                score=float(point.score or 0.0),
                text=str(
                    point.payload.get("content") or point.payload.get("text") or ""
                ),
                metadata=dict(point.payload),
            )
            for point in points
        ]

        if not use_rerank or not hits:
            return hits

        reranked = self.reranker.rerank(
            query=question,
            texts=[item.text for item in hits],
            top_k=min(settings.qdrant_max_chunks_reranked, len(hits)),
        )
        return [hits[idx] for idx, _score in reranked]

    # ────────────────────────────────────────────────────────────────
    def answer(
        self,
        question: str,
        use_rerank: bool = True,
        conversation_history: str | None = None,
    ) -> dict:
        """Genera una respuesta usando RAG, con contexto recuperado y reranking opcional."""
        hits = self.retrieve(question=question, use_rerank=use_rerank)
        context = "\n\n".join([item.text for item in hits])
        prompt_question = question
        if conversation_history:
            prompt_question = (
                "Historial reciente de la conversacion:\n"
                f"{conversation_history}\n\n"
                "Pregunta actual:\n"
                f"{question}"
            )

        prompt = RAG_USER_PROMPT_TEMPLATE.format(
            question=prompt_question,
            context=context,
        )
        llm = self._build_llm_client()
        answer = llm.generate(prompt=prompt, system_prompt=RAG_SYSTEM_PROMPT)

        return {
            "question": question,
            "answer": answer,
            "context_hits": [
                {
                    "score": item.score,
                    "metadata": item.metadata,
                }
                for item in hits
            ],
        }

    # ────────────────────────────────────────────────────────────────
    def _build_llm_client(self):
        """Construye el cliente LLM adecuado según el proveedor configurado."""
        provider = (self.llm_provider or settings.llm_provider).lower()
        model_name = self.llm_model_name or settings.llm_model_name
        model_path = self.llm_model_path or settings.llm_model_path

        if provider == "ollama":
            return OllamaClient(
                base_url=settings.ollama_base_url,
                model=model_name,
            )
        if provider in {"openai", "chatgpt"}:
            if not settings.openai_api_key:
                raise RuntimeError(
                    "OPENAI_API_KEY is required when llm_provider is openai/chatgpt"
                )
            return OpenAIClient(
                api_key=settings.openai_api_key,
                model=model_name,
            )
        if provider in {"claude", "bedrock"}:
            resolved_model_id = model_name or settings.bedrock_model_id
            return BedrockClient(model_id=resolved_model_id)

        return LlamaCppClient(
            model_path=self._resolve_llama_model_path(model_path),
        )

    # ────────────────────────────────────────────────────────────────
    def _resolve_llama_model_path(self, model_path: str) -> str:
        """Resuelve la ruta local del modelo Llama, descargando desde S3 si es necesario."""
        if not model_path.startswith("s3://"):
            return model_path

        # Expected format: s3://bucket/path/to/model.gguf
        without_scheme = model_path[5:]
        if "/" not in without_scheme:
            raise RuntimeError("Invalid s3 model path format")

        _bucket, key = without_scheme.split("/", 1)
        filename = os.path.basename(key)
        local_dir = Path("/tmp/llm_models")
        local_dir.mkdir(parents=True, exist_ok=True)
        local_path = local_dir / filename

        if local_path.exists() and local_path.stat().st_size > 0:
            return str(local_path)

        storage = S3Storage()
        folder = os.path.dirname(key)
        object_name = os.path.basename(key)
        binary = storage.read_file(folder, object_name)
        local_path.write_bytes(binary)
        return str(local_path)
