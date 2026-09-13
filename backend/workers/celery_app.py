from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "diagnoz",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["workers.tasks.media_transcode"],
)

celery_app.conf.update(task_serializer="json", result_serializer="json", accept_content=["json"])
