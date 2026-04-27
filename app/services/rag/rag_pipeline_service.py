from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import datetime, timezone
from functools import lru_cache
from io import BytesIO
from typing import List

import httpx
import pdf2image
import pytesseract
from pypdf import PdfReader
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.models.document_chunk import DocumentChunk
from app.models.document_file import DocumentFile
from app.models.document_section import DocumentSection
from app.models.scraped_document import ScrapedDocument
from app.rag.chunking import RecursiveTextChunker
from app.rag.embeddings import SentenceTransformerEmbeddingClient
from app.rag.vectorstore import QdrantVectorStore
from app.services.s3_storage import S3Storage

PDF_TIMEOUT_SECONDS = 60


class RagIngestionService:
    """Servicio para la ingesta y vectorización de documentos HTML y PDF."""

    # ────────────────────────────────────────────────────────────────
    def __init__(self):
        """Inicializa los componentes de chunking, embeddings y almacenamiento."""
        self.chunker = RecursiveTextChunker(
            chunk_size=settings.rag_chunk_size,
            chunk_overlap=settings.rag_chunk_overlap,
        )
        self.embedder = SentenceTransformerEmbeddingClient(settings.rag_embedding_model)
        self.vector_store = QdrantVectorStore(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
            grpc_port=settings.qdrant_grpc_port,
            collection_name=settings.qdrant_collection_name,
            vector_size=self.embedder.embedding_dimension(),
        )
        self.storage = S3Storage()

    # ────────────────────────────────────────────────────────────────
    def vectorize_scraped_html(self, db: Session, scraped_document_id: int) -> dict:
        """Vectoriza el texto de un documento HTML scrapeado y lo almacena."""
        doc = db.get(ScrapedDocument, scraped_document_id)
        if not doc:
            raise ValueError(f"ScrapedDocument {scraped_document_id} not found")

        base_metadata = {
            "source_type": "html",
            "scraped_document_id": doc.id,
            "doc_id": doc.doc_id,
            "title": doc.title or "Sin titulo",
            "url": doc.final_url or doc.url,
        }

        text = (doc.text or "").strip()
        if not text:
            raise ValueError(f"ScrapedDocument {scraped_document_id} has empty text")

        self._store_sections_from_html(db, doc)
        chunks = self.chunker.chunk(text, base_metadata)
        self._persist_chunks(db=db, scraped_document_id=doc.id, chunks=chunks)
        doc.status = "vectorized"
        db.commit()

        return {"scraped_document_id": doc.id, "chunks": len(chunks), "source": "html"}

    # ────────────────────────────────────────────────────────────────
    def process_and_vectorize_pdf_file(
        self, db: Session, document_file_id: int
    ) -> dict:
        """Procesa y vectoriza un archivo PDF, aplicando OCR si es necesario."""
        file_row = db.get(DocumentFile, document_file_id)
        if not file_row:
            raise ValueError(f"DocumentFile {document_file_id} not found")

        parent_doc = db.get(ScrapedDocument, file_row.scraped_document_id)
        if not parent_doc:
            raise ValueError(
                f"ScrapedDocument {file_row.scraped_document_id} not found for file {document_file_id}"
            )

        pdf_bytes = self._download_pdf(file_row.file_url)
        object_name = (
            f"{file_row.id}_{self._sanitize_filename(file_row.title or 'document')}.pdf"
        )
        folder = f"documents/raw/{parent_doc.doc_id}"
        storage_path = self.storage.write_file(folder, object_name, pdf_bytes)

        text = self._extract_pdf_text_with_ocr_fallback(pdf_bytes)
        if not text.strip():
            raise ValueError(f"No text extracted from PDF file {document_file_id}")

        base_metadata = {
            "source_type": "pdf",
            "scraped_document_id": parent_doc.id,
            "document_file_id": file_row.id,
            "doc_id": parent_doc.doc_id,
            "title": file_row.title or parent_doc.title or "PDF",
            "file_url": file_row.file_url,
            "source_url": parent_doc.final_url or parent_doc.url,
        }

        chunks = self.chunker.chunk(text, base_metadata)
        self._persist_chunks(db=db, scraped_document_id=parent_doc.id, chunks=chunks)

        file_row.file_path = storage_path
        file_row.summary = text[:1000]
        file_row.status = "processed"
        file_row.processed_at = datetime.now(timezone.utc)

        if parent_doc.status != "vectorized":
            parent_doc.status = "vectorized"

        db.commit()
        return {
            "document_file_id": file_row.id,
            "scraped_document_id": parent_doc.id,
            "chunks": len(chunks),
            "storage_path": storage_path,
            "source": "pdf",
        }

    # ────────────────────────────────────────────────────────────────
    def _persist_chunks(self, db: Session, scraped_document_id: int, chunks) -> None:
        """Guarda los chunks vectorizados en la base de datos y el vector store."""
        texts = [item.content for item in chunks]
        vectors = self.embedder.embed_texts(texts)

        ids: List[str] = []
        payloads: List[dict] = []
        rows: List[DocumentChunk] = []

        for chunk, vector in zip(chunks, vectors):
            point_id = str(uuid.uuid4())
            chunk_id = str(uuid.uuid4())
            payload = dict(chunk.metadata)
            payload.update(
                {
                    "content": chunk.content,
                    "chunk_id": chunk_id,
                    "chunk_index": chunk.index,
                    "content_hash": hashlib.md5(
                        chunk.content.encode("utf-8")
                    ).hexdigest(),
                }
            )

            ids.append(point_id)
            payloads.append(payload)
            rows.append(
                DocumentChunk(
                    scraped_document_id=scraped_document_id,
                    chunk_id=chunk_id,
                    chunk_index=chunk.index,
                    content=chunk.content,
                    token_count=max(1, len(chunk.content.split())),
                    qdrant_collection=settings.qdrant_collection_name,
                    qdrant_point_id=point_id,
                    embedding_model=settings.rag_embedding_model,
                    chunk_metadata=payload,
                    status="vectorized",
                    error_message=None,
                    created_at=datetime.now(timezone.utc),
                )
            )

        self.vector_store.upsert(ids=ids, vectors=vectors, payloads=payloads)
        db.add_all(rows)
        db.flush()

    # ────────────────────────────────────────────────────────────────
    def _store_sections_from_html(self, db: Session, doc: ScrapedDocument) -> None:
        """Guarda las secciones del documento HTML en la base de datos."""
        headings = []
        if doc.headings:
            try:
                headings = json.loads(doc.headings)
            except Exception:
                headings = []

        text = (doc.text or "").strip()
        if not text:
            return

        if not headings:
            db.add(
                DocumentSection(
                    scraped_document_id=doc.id,
                    heading=doc.title or "Contenido",
                    content=text,
                    position=1,
                    created_at=datetime.now(timezone.utc),
                )
            )
            db.flush()
            return

        paragraphs = [
            part.strip() for part in re.split(r"\n{2,}", text) if part.strip()
        ]
        grouped = []
        bucket_size = max(1, len(paragraphs) // len(headings))
        for i, heading in enumerate(headings, start=1):
            start = (i - 1) * bucket_size
            end = i * bucket_size if i < len(headings) else len(paragraphs)
            content = "\n\n".join(paragraphs[start:end]).strip() or text
            grouped.append((heading, content, i))

        for heading, content, position in grouped:
            db.add(
                DocumentSection(
                    scraped_document_id=doc.id,
                    heading=heading,
                    content=content,
                    position=position,
                    created_at=datetime.now(timezone.utc),
                )
            )
        db.flush()

    # ────────────────────────────────────────────────────────────────
    def _download_pdf(self, url: str) -> bytes:
        """Descarga un archivo PDF desde una URL y retorna su contenido en bytes."""
        with httpx.Client(timeout=PDF_TIMEOUT_SECONDS, follow_redirects=True) as client:
            response = client.get(url)
            response.raise_for_status()
            return response.content

    # ────────────────────────────────────────────────────────────────
    def _extract_pdf_text_with_ocr_fallback(self, pdf_bytes: bytes) -> str:
        """Extrae texto de un PDF, usando OCR si es necesario."""
        reader = PdfReader(BytesIO(pdf_bytes))
        page_texts: List[str] = []

        for page_index, page in enumerate(reader.pages, start=1):
            text = (page.extract_text() or "").strip()
            if text:
                page_texts.append(text)
                continue

            ocr_text = self._ocr_page(pdf_bytes, page_index)
            if ocr_text.strip():
                page_texts.append(ocr_text.strip())

        return "\n\n".join(page_texts)

    # ────────────────────────────────────────────────────────────────
    def _ocr_page(self, pdf_bytes: bytes, page_number: int) -> str:
        """Realiza OCR sobre una página específica de un PDF."""
        images = pdf2image.convert_from_bytes(
            pdf_bytes,
            dpi=200,
            first_page=page_number,
            last_page=page_number,
        )
        if not images:
            return ""
        return pytesseract.image_to_string(images[0])

    # ────────────────────────────────────────────────────────────────
    def _sanitize_filename(self, value: str) -> str:
        """Limpia y limita el nombre de archivo para almacenamiento seguro."""
        safe = re.sub(r"[^a-zA-Z0-9_-]", "_", value)
        return safe[:80] or "document"


# ────────────────────────────────────────────────────────────────
@lru_cache(maxsize=1)
def get_rag_ingestion_service() -> RagIngestionService:
    """Devuelve una instancia cacheada de RagIngestionService."""
    return RagIngestionService()
