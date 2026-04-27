from __future__ import annotations

from typing import Dict, List, Sequence

from qdrant_client import QdrantClient, models

from app.rag.vectorstore.base import BaseVectorStore


# ─────────────────────────────────────────────────────────────
class QdrantVectorStore(BaseVectorStore):
    """Almacén de vectores basado en Qdrant para operaciones de búsqueda y upsert."""

    # ─────────────────────────────────────────────────────────────
    def __init__(
        self,
        host: str,
        port: int,
        grpc_port: int,
        collection_name: str,
        vector_size: int,
    ):
        """Inicializa el almacén Qdrant y asegura la colección."""
        self.collection_name = collection_name
        self._client = QdrantClient(
            host=host, port=port, grpc_port=grpc_port, timeout=30
        )
        self._ensure_collection(vector_size=vector_size)

    # ─────────────────────────────────────────────────────────────
    def _ensure_collection(self, vector_size: int) -> None:
        """Crea la colección en Qdrant si no existe."""
        collections = self._client.get_collections().collections
        existing = {item.name for item in collections}
        if self.collection_name in existing:
            return

        self._client.create_collection(
            collection_name=self.collection_name,
            vectors_config=models.VectorParams(
                size=vector_size, distance=models.Distance.COSINE
            ),
        )

    # ─────────────────────────────────────────────────────────────
    def upsert(
        self,
        ids: Sequence[str],
        vectors: Sequence[List[float]],
        payloads: Sequence[Dict[str, object]],
    ) -> None:
        """Inserta o actualiza vectores y payloads en la colección."""
        self._client.upsert(
            collection_name=self.collection_name,
            points=models.Batch(
                ids=list(ids),
                vectors=list(vectors),
                payloads=list(payloads),
            ),
        )

    # ─────────────────────────────────────────────────────────────
    def search(
        self,
        query_vector: List[float],
        limit: int,
        filter_payload: Dict[str, object] | None = None,
    ):
        """Realiza una búsqueda de vectores similares en la colección."""
        query_filter = None
        if filter_payload:
            must = [
                models.FieldCondition(
                    key=key,
                    match=models.MatchValue(value=value),
                )
                for key, value in filter_payload.items()
            ]
            query_filter = models.Filter(must=must)

        response = self._client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            query_filter=query_filter,
            limit=limit,
        )
        return response.points
