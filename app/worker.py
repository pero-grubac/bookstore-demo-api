"""Celery application (Redis as broker).

Start a worker with:
    celery -A app.worker:celery_app worker --loglevel=info
"""

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "bookstore",
    broker=settings.CELERY_BROKER_URL,
    include=["app.features.orders.tasks"],
)
celery_app.conf.update(
    task_ignore_result=True,  # tasks only have side effects, no result backend
    broker_connection_retry_on_startup=True,
    # If Redis is down, fail fast instead of blocking the HTTP request.
    task_publish_retry=False,
    broker_connection_timeout=2,
    broker_transport_options={"socket_connect_timeout": 2, "socket_timeout": 2},
)
