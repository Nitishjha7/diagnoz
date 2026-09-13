from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "diagnoz",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "workers.tasks.media_transcode",
        "workers.tasks.report_generate",
        "workers.tasks.payout_settle",
    ],
)

celery_app.conf.update(task_serializer="json", result_serializer="json", accept_content=["json"])

celery_app.conf.beat_schedule = {
    "weekly-payout-settlement": {
        "task": "tasks.settle_payouts",
        "schedule": crontab(hour=2, minute=0, day_of_week=1),  # every Monday 02:00
    },
}
