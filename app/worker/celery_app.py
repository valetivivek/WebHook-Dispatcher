from celery import Celery

from app.config import settings
from app.logging import setup_logging

setup_logging()

celery_app = Celery(
    "webhook_dispatcher",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # At-least-once: ack after task completes, not when received
    task_acks_late=True,
    # Reject and re-queue if worker is killed
    task_reject_on_worker_lost=True,
    # Only prefetch 1 task at a time per worker for fair distribution
    worker_prefetch_multiplier=1,
)

celery_app.autodiscover_tasks(["app.worker"])
