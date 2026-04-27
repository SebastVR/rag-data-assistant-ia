from fastapi import APIRouter, Query

from app.services.admin.db_populate_service import (
    populate_scraped_documents_from_prefix,
)

router = APIRouter(prefix="/api/v1/admin", tags=["etl"])


# ─────────────────────────────────────────────────────────────
@router.post("/populate-db")
def populate_db(
    prefix: str = Query(
        ..., description="Prefijo S3/carpeta de scraping (ej: bbva_html)"
    ),
):
    """Pobla la base de datos usando el prefijo indicado."""
    result = populate_scraped_documents_from_prefix(prefix)
    return result
