from celery import Celery, signals
from config.config import Settings, initiate_database
from config.logging_config import setup_logging
import asyncio

# Celery metrics monitoring removed - focusing on FastAPI only

setup_logging()  

def make_celery():
    settings = Settings()
    celery_app = Celery(
        "worker",
        broker=settings.REDIS_URL,
        backend=settings.REDIS_URL,
        include=["service.routine_service", "service.tracker_service"]
    )

    celery_app.conf.update(
        task_routes={
            "app.services.*": {"queue": "default"},
        },
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        timezone="Asia/Ho_Chi_Minh",  
        enable_utc=True,
    )
    return celery_app

celery_app = make_celery()

@signals.worker_process_init.connect
def init_worker(**kwargs):
    """Initialize the database when the worker starts."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(initiate_database())
    finally:
        loop.close()

if __name__ == "__main__":
    celery_app.start()