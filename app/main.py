from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config.settings import settings
from app.db.base import Base
from app.db.db_connection import SessionLocal, engine
from app.routers.admin.populate_router import router as populate_router
from app.routers.analytics.analytics_router import router as analytics_router
from app.routers.db.connection_router import router as connection_router
from app.routers.db.document_router import router as document_router
from app.routers.db.model_router import router as model_router
from app.routers.db.scraping_run_router import router as scraping_run_router
from app.routers.llm.llm_router import router as llm_router
from app.routers.rag.rag_router import router as rag_router
from app.routers.rerank.rerank_router import router as rerank_router
from app.routers.scraping.scraping_router import router as scraping_router
from app.services.llm.language_model_registry import ensure_default_language_models

api = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="RAG Banking Assistant with Web Scraping",
    openapi_tags=[
        {"name": "scraping", "description": "Crawler y procesamiento web"},
        {"name": "etl", "description": "Procesos de carga y poblamiento"},
        {"name": "rag", "description": "Ingestion, consulta y estado de RAG"},
        {"name": "db", "description": "Utilidades de base de datos"},
        {"name": "db:scraping", "description": "Lecturas de modelos de scraping"},
        {"name": "db:documents", "description": "Lecturas de modelos de documentos"},
        {"name": "db:models", "description": "Lecturas de modelos internos"},
        {"name": "llm", "description": "Gestion de modelos LLM y runtime"},
        {"name": "analytics", "description": "Metricas de uso, costos y latencia"},
    ],
)


api.include_router(scraping_router)
api.include_router(connection_router)
api.include_router(populate_router)
api.include_router(rag_router)
api.include_router(document_router)
api.include_router(scraping_run_router)
api.include_router(model_router)
api.include_router(llm_router)
api.include_router(rerank_router)
api.include_router(analytics_router)


@api.get("/")
def root():
    return {
        "message": "RAG Bank Assistant API is running",
        "app_name": settings.app_name,
    }


@api.get("/health")
def health_check():
    return {
        "status": "ok",
        "app_name": settings.app_name,
        "scraper_base_url": settings.scraper_base_url,
        "allowed_domain": settings.scraper_allowed_domain,
    }


# -------------------------------------------------------------------
# 🔧 Helpers para error handling
# -------------------------------------------------------------------
_CODE_MAP = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    408: "REQUEST_TIMEOUT",
    409: "CONFLICT",
    422: "UNPROCESSABLE_ENTITY",
    429: "TOO_MANY_REQUESTS",
    500: "INTERNAL_SERVER_ERROR",
    502: "BAD_GATEWAY",
    503: "SERVICE_UNAVAILABLE",
    504: "GATEWAY_TIMEOUT",
}


def _msg_for(code: int) -> str:
    return _CODE_MAP.get(code, "ERROR")


def _safe_detail(detail) -> str:
    try:
        return detail if isinstance(detail, str) else str(detail)
    except Exception:
        return "Error"


def _error_payload(code: int, detail: str, request: Request) -> dict:
    return {
        "message": _msg_for(code),
        "detail": _safe_detail(detail),
        "status_code": code,
    }


# -------------------------------------------------------------------
# ❗ Handlers globales de errores
# -------------------------------------------------------------------


@api.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=400,
        content=_error_payload(400, exc.errors(), request),
    )


@api.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    code = exc.status_code
    defaults = {
        404: f"Route '{request.url.path}' not found.",
        405: f"Method '{request.method}' not allowed for '{request.url.path}'.",
        401: "Authentication required.",
        403: "You do not have permission to access this resource.",
    }
    detail = exc.detail or defaults.get(code, "Request error.")
    return JSONResponse(status_code=code, content=_error_payload(code, detail, request))


@api.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content=_error_payload(500, str(exc), request),
    )


try:
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        seed_result = ensure_default_language_models(db)
    finally:
        db.close()
    print("✅ Tablas creadas o ya existentes en la base de datos.")
    print(
        "✅ LanguageModel seed aplicado: "
        f"created={seed_result['created']} "
        f"updated={seed_result['updated']}"
    )
except Exception as e:
    print(f"❌ Error al crear las tablas: {e}")
