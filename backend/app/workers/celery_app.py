from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "interviewos",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "purge-expired-media": {
            "task": "app.workers.tasks.purge_expired_media",
            "schedule": 3600.0,
        }
    },
)
