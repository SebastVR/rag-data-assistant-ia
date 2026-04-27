from sqlalchemy import func

from app.models.document_chunk import DocumentChunk
from app.models.document_file import DocumentFile


# ────────────────────────────────────────────────────────────────
def get_vectorization_totals(db) -> dict:
    """Devuelve métricas totales de vectorización de documentos y chunks."""
    vectorized_chunks = (
        db.query(func.count(DocumentChunk.id))
        .filter(DocumentChunk.status == "vectorized")
        .scalar()
        or 0
    )

    vectorized_documents = (
        db.query(func.count(func.distinct(DocumentChunk.scraped_document_id)))
        .filter(DocumentChunk.status == "vectorized")
        .scalar()
        or 0
    )

    vectorized_pdf_documents = (
        db.query(func.count(DocumentFile.id))
        .filter(DocumentFile.status == "processed")
        .scalar()
        or 0
    )

    return {
        "vectorized_documents": int(vectorized_documents),
        "vectorized_pdf_documents": int(vectorized_pdf_documents),
        "vectorized_chunks": int(vectorized_chunks),
    }
