from __future__ import annotations

import os

from celery.result import AsyncResult
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.celery_worker.tasks import upload_llm_model_task
from app.controllers.llm.model_management_controller import (
    activate_llm_model,
    activate_llm_model_by_id,
    list_llm_model_options,
)
from app.db.db_connection import get_db
from app.schemas.llm import ActivateModelByIdRequest, ActivateModelRequest
from app.services.llm.runtime_config_service import get_runtime_llm_config
from app.services.s3_storage import save_model_file_to_minio

# --- NUEVO: Endpoint para consultar el estado de una tarea Celery ---

router = APIRouter(prefix="/api/v1/llm", tags=["llm"])


# ─────────────────────────────────────────────────────────────
@router.get("/models/upload/status/{task_id}")
def get_upload_task_status(task_id: str):
    """Consulta el estado de una tarea de subida de modelo."""
    result = AsyncResult(task_id)
    response = {
        "task_id": task_id,
        "state": result.state,
        "ready": result.ready(),
        "successful": result.successful() if result.ready() else None,
        "result": None,
        "error": None,
    }
    if result.ready():
        if result.successful():
            response["result"] = result.result
        else:
            response["error"] = str(result.result)
    return response


# ─────────────────────────────────────────────────────────────
@router.post("/models/upload")
async def upload_model(
    file: UploadFile = File(...),
    provider: str = Form(default="llama_cpp"),
    model_name: str | None = Form(default=None),
    input_token_cost: float = Form(default=2.5),
    output_token_cost: float = Form(default=5.0),
    set_as_active: bool = Form(default=True),
):
    """Sube un modelo LLM usando Celery."""
    try:
        normalized_provider = provider.strip().lower()
        if normalized_provider != "llama_cpp":
            raise HTTPException(
                status_code=400,
                detail="/models/upload solo soporta provider=llama_cpp (.gguf)",
            )

        if not file.filename:
            raise HTTPException(status_code=400, detail="filename es requerido")

        ext = os.path.splitext(file.filename)[1].lower()
        if ext != ".gguf":
            raise HTTPException(
                status_code=400,
                detail="Solo se permiten archivos .gguf",
            )

        # 1. Subir archivo a MinIO/S3

        file_key = save_model_file_to_minio(file, folder="llm_models")

        resolved_model_name = model_name or os.path.splitext(file.filename)[0]
        # 2. Lanzar tarea Celery pasando solo el file_key (no el path local)
        task = upload_llm_model_task.delay(
            file_key=file_key,
            file_name=file.filename,
            provider=normalized_provider,
            model_name=resolved_model_name.strip(),
            input_token_cost=input_token_cost,
            output_token_cost=output_token_cost,
            set_as_active=set_as_active,
        )
        return {
            "message": "Model upload task launched",
            "task_id": task.id,
            "file_key": file_key,
        }
    except HTTPException:
        raise
    except TypeError as e:
        raise HTTPException(status_code=501, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────
@router.get("/models/active")
def get_active_model(db=Depends(get_db)):
    """Obtiene el modelo LLM activo actualmente."""
    try:
        return get_runtime_llm_config(db)
    except TypeError as e:
        raise HTTPException(status_code=501, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────
@router.get("/models/options")
def get_model_options(provider: str | None = None, db=Depends(get_db)):
    """Lista las opciones de modelos LLM disponibles."""
    try:
        runtime = get_runtime_llm_config(db)
        options = list_llm_model_options(db=db, provider=provider)
        options["active"] = {
            "provider": runtime.get("llm_provider"),
            "model_name": runtime.get("llm_model_name"),
            "model_path": runtime.get("llm_model_path"),
        }
        return options
    except TypeError as e:
        raise HTTPException(status_code=501, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────
@router.post("/models/activate")
def activate_model(payload: ActivateModelRequest, db=Depends(get_db)):
    """Activa un modelo LLM específico."""
    try:
        result = activate_llm_model(
            db=db,
            provider=payload.provider,
            model_name=payload.model_name,
            model_path=payload.model_path,
            set_as_active=payload.set_as_active,
        )
        return {
            "message": "Model activation processed",
            **result,
        }
    except TypeError as e:
        raise HTTPException(status_code=501, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────
@router.post("/models/activate/by-id")
def activate_model_by_id(payload: ActivateModelByIdRequest, db=Depends(get_db)):
    """Activa un modelo LLM por ID."""
    try:
        result = activate_llm_model_by_id(
            db=db,
            language_model_id=payload.language_model_id,
            set_as_active=payload.set_as_active,
        )
        return {
            "message": "Model activation processed",
            **result,
        }
    except TypeError as e:
        raise HTTPException(status_code=501, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
