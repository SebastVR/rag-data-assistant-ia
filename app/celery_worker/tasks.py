from decimal import Decimal

from celery.utils.log import get_task_logger

from app.celery_worker.celery_config import celery_app
from app.controllers.llm.model_management_controller import upload_llm_model
from app.db.db_connection import SessionLocal
from app.models.document_file import DocumentFile
from app.models.scraped_document import ScrapedDocument
from app.services.rag.rag_pipeline_service import get_rag_ingestion_service

logger = get_task_logger(__name__)


# ─────────────────────────────────────────────────────────────
@celery_app.task(
    name="rag.process_pdf_file_task",
    queue="rag-data-assistant-ia",
    acks_late=True,
)
def process_pdf_file_task(document_file_id: int):
    """Procesa y vectoriza un archivo PDF por su ID."""
    db = SessionLocal()
    try:
        rag_ingestion_service = get_rag_ingestion_service()
        logger.info("Processing PDF file id=%s", document_file_id)
        result = rag_ingestion_service.process_and_vectorize_pdf_file(
            db=db,
            document_file_id=document_file_id,
        )
        logger.info(
            "PDF file processed id=%s chunks=%s", document_file_id, result["chunks"]
        )
        return result
    except Exception as exc:
        file_row = db.get(DocumentFile, document_file_id)
        if file_row:
            file_row.status = "failed"
            file_row.error_message = str(exc)
            db.commit()
        logger.exception("Error processing PDF file id=%s", document_file_id)
        raise
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────
@celery_app.task(
    name="rag.vectorize_html_document_task",
    queue="rag-data-assistant-ia",
    acks_late=True,
)
def vectorize_html_document_task(scraped_document_id: int):
    """Vectoriza un documento HTML extraído por su ID."""
    db = SessionLocal()
    try:
        rag_ingestion_service = get_rag_ingestion_service()
        logger.info("Vectorizing HTML doc id=%s", scraped_document_id)
        result = rag_ingestion_service.vectorize_scraped_html(
            db=db,
            scraped_document_id=scraped_document_id,
        )
        logger.info(
            "HTML doc vectorized id=%s chunks=%s", scraped_document_id, result["chunks"]
        )
        return result
    except Exception as exc:
        doc = db.get(ScrapedDocument, scraped_document_id)
        if doc:
            doc.status = "failed"
            doc.error_message = str(exc)
            db.commit()
        logger.exception("Error vectorizing HTML doc id=%s", scraped_document_id)
        raise
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────
@celery_app.task(
    name="rag.process_pending_ingestion_task",
    queue="rag-data-assistant-ia",
    acks_late=True,
)
def process_pending_ingestion_task(limit: int = 20):
    """Lanza tareas pendientes de vectorización de HTML y PDF."""
    db = SessionLocal()
    launched = {
        "html_jobs": 0,
        "pdf_jobs": 0,
    }
    try:
        pending_html = (
            db.query(ScrapedDocument)
            .filter(ScrapedDocument.status == "processed")
            .order_by(ScrapedDocument.id.asc())
            .limit(limit)
            .all()
        )
        for row in pending_html:
            vectorize_html_document_task.delay(row.id)
            launched["html_jobs"] += 1

        pending_pdf = (
            db.query(DocumentFile)
            .filter(DocumentFile.file_type == "pdf", DocumentFile.status == "pending")
            .order_by(DocumentFile.id.asc())
            .limit(limit)
            .all()
        )
        for row in pending_pdf:
            process_pdf_file_task.delay(row.id)
            launched["pdf_jobs"] += 1

        logger.info(
            "Dispatched ingestion jobs html=%s pdf=%s",
            launched["html_jobs"],
            launched["pdf_jobs"],
        )
        return launched
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────


@celery_app.task(
    name="llm.upload_llm_model_task",
    queue="rag-data-assistant-ia",
    acks_late=True,
)
def upload_llm_model_task(
    file_key: str,
    file_name: str,
    provider: str,
    model_name: str,
    input_token_cost: float,
    output_token_cost: float,
    set_as_active: bool,
):
    """Descarga el modelo desde MinIO/S3 y lo registra en la base de datos."""
    db = SessionLocal()
    try:
        from app.services.s3_storage import S3Storage

        s3 = S3Storage()
        folder, object_name = file_key.rsplit("/", 1)
        file_bytes = s3.read_file(folder, object_name)
        result = upload_llm_model(
            db=db,
            file_name=file_name,
            file_bytes=file_bytes,
            provider=provider,
            model_name=model_name,
            input_token_cost=Decimal(str(input_token_cost)),
            output_token_cost=Decimal(str(output_token_cost)),
            set_as_active=set_as_active,
        )
        logger.info(f"Modelo {model_name} subido y registrado correctamente.")
        return result
    except Exception as exc:
        logger.exception(f"Error subiendo modelo {model_name}: {exc}")
        raise
    finally:
        db.close()
