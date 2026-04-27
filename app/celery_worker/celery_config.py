# app/celery_worker/celery_config.py
from celery import Celery
from kombu import Queue

from app.config.settings import settings

celery_app = Celery(
    "celery_worker",
    broker=settings.celery_broker_url,  # redis://redis:6379/0
    backend=settings.celery_backend_url,  # redis://redis:6379/1
    include=["app.celery_worker.tasks"],  # o usa autodiscovery si prefieres
)

celery_app.conf.update(
    task_track_started=True,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    enable_utc=True,
    timezone="UTC",
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    broker_heartbeat=30,
    broker_pool_limit=10,
    # Configuración de concurrencia y limits
    worker_concurrency=2,
    worker_max_tasks_per_child=1000,
    # 🔒 Cola dedicada
    task_default_queue="rag-data-assistant-ia",
    task_queues=[Queue("rag-data-assistant-ia")],
    task_routes={
        "app.*": {"queue": "rag-data-assistant-ia"},
    },
)

__all__ = ("celery_app",)
