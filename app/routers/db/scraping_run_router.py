from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.controllers.db.documents_controller import _to_iso
from app.db.db_connection import get_db
from app.models.scraping_run import ScrapingRun

router = APIRouter(prefix="/api/v1/db/scraping/runs", tags=["db:scraping"])


# ─────────────────────────────────────────────────────────────
@router.get("/", summary="Listar ejecuciones de scraping", response_model=None)
def list_scraping_runs(
    db: Session = Depends(get_db),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Lista las ejecuciones de scraping realizadas."""
    query = db.query(ScrapingRun).order_by(ScrapingRun.id.desc())
    total = query.count()
    runs = query.offset(offset).limit(limit).all()
    items = []
    for run in runs:
        items.append(
            {
                "id": run.id,
                "source_name": run.source_name,
                "base_url": run.base_url,
                "allowed_domain": run.allowed_domain,
                "max_pages": run.max_pages,
                "status": run.status,
                "pages_found": run.pages_found,
                "pages_processed": run.pages_processed,
                "pages_failed": run.pages_failed,
                "error_message": run.error_message,
                "started_at": _to_iso(run.started_at),
                "finished_at": _to_iso(run.finished_at),
                "created_at": _to_iso(run.created_at),
            }
        )
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": items,
    }
