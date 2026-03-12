from celery import Celery

from app.core.config import settings


celery_app = Celery(
    "transcribely",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.video_processor"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max
    worker_prefetch_multiplier=1,  # Process one task at a time per worker
)
