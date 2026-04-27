import json
import re
from datetime import datetime

from sqlalchemy.exc import IntegrityError

from app.db.db_connection import SessionLocal
from app.models.document_file import DocumentFile
from app.models.scraped_document import ScrapedDocument
from app.models.scraping_run import ScrapingRun
from app.services.scraping.html_processing_service import (
    process_all_html_and_return_json,
)

PDF_URL_RE = re.compile(r"https?://[^\s\"'<>]+?\.pdf(?:\?[^\s\"'<>]*)?", re.IGNORECASE)


# ────────────────────────────────────────────────────────────────
def _extract_pdf_urls(doc: dict) -> set[str]:
    """
    Extrae URLs PDF desde texto, headings y URLs fuente del documento.
    """
    candidates = [
        doc.get("text") or "",
        json.dumps(doc.get("headings", []), ensure_ascii=False),
        doc.get("source_url") or "",
        doc.get("url") or "",
    ]

    urls: set[str] = set()
    for field in candidates:
        for raw_url in PDF_URL_RE.findall(field):
            # Limpia signos de puntuacion de cierre que puedan quedar pegados al enlace.
            urls.add(raw_url.rstrip(").,;:!?"))
    return urls


# ────────────────────────────────────────────────────────────────
def populate_scraped_documents_from_prefix(prefix: str):
    """
    Usa process_all_html_and_return_json para obtener los docs
    y poblar la base de datos.
    Crea un scraping_run si no existe.
    """
    docs = process_all_html_and_return_json(prefix)
    return _populate_scraped_documents(docs, prefix)


# ────────────────────────────────────────────────────────────────
def _populate_scraped_documents(docs: dict, prefix: str):
    """
    Lee el JSON de documentos únicos y los inserta en la base de datos.
    Extrae y registra PDFs en DocumentFile.
    """
    session = SessionLocal()
    # Buscar o crear scraping_run
    run = session.query(ScrapingRun).filter_by(base_url=prefix).first()
    if not run:
        run = ScrapingRun(
            source_name="web_scraping",
            base_url=prefix,
            allowed_domain=prefix.replace("_html", ".com.co"),
            max_pages=100,
            status="completed",
            pages_found=len(docs),
            pages_processed=len(docs),
            pages_failed=0,
            error_message=None,
            started_at=datetime.utcnow(),
            finished_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
        )
        session.add(run)
        session.commit()
    scraping_run_id = run.id
    inserted = 0
    skipped = 0
    pdfs = 0
    for doc_id, doc in docs.items():
        # Evitar duplicados por content_hash o doc_id
        exists = session.query(ScrapedDocument).filter_by(doc_id=doc_id).first()
        if exists:
            skipped += 1
            continue
        scraped_doc = ScrapedDocument(
            scraping_run_id=scraping_run_id,
            doc_id=doc_id,
            source_name="web_scraping",
            url=doc.get("url"),
            final_url=doc.get("source_url"),
            title=doc.get("title"),
            category="general",
            headings=json.dumps(doc.get("headings", [])),
            text=doc.get("text"),
            raw_file_path=doc.get("file"),
            processed_file_path=None,
            content_hash=None,
            status="processed",
            error_message=None,
            scraped_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
        )
        session.add(scraped_doc)
        session.flush()
        inserted += 1
        # Buscar PDFs en contenido y metadatos del documento.
        pdf_links = _extract_pdf_urls(doc)
        for pdf_url in pdf_links:
            # Extraer el título del PDF desde la URL
            match = re.search(r"/([^/]+\.pdf)(?:\?|$)", pdf_url)
            pdf_title = match.group(1) if match else None
            if not pdf_title:
                continue
            # Verificar si ya existe un PDF con ese título
            existing_pdf = (
                session.query(DocumentFile).filter_by(title=pdf_title).first()
            )
            if existing_pdf:
                continue
            pdf_file = DocumentFile(
                scraped_document_id=scraped_doc.id,
                file_url=pdf_url,
                file_type="pdf",
                file_path=None,
                content_hash=None,
                title=pdf_title,
                summary=None,
                status="pending",
                error_message=None,
                processed_at=None,
                created_at=datetime.utcnow(),
            )
            session.add(pdf_file)
            pdfs += 1
    try:
        session.commit()
    except IntegrityError as e:
        session.rollback()
        return {"error": str(e)}
    finally:
        session.close()
    return {"inserted": inserted, "skipped": skipped, "pdfs": pdfs}
