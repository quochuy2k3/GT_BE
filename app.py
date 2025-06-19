import asyncio

from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI, Depends
from prometheus_fastapi_instrumentator import Instrumentator

from config.jwt_bearer import JWTBearer
from monitoring.fastapi_metrics import app_info
from config.config import initiate_database
from routes.admin import router as AdminRouter
from routes.auth import router as AuthRouter
from routes.media import router as MediaRouter
from routes.routine import router as RoutineRouter
from routes.user import router as UserRouter
from routes.couple import router as CoupleRouter
from routes.gemini import router as GeminiRouter
from service.routine_service import cron_notification, reset_sessions_status, mark_not_done
from service.tracker_service import update_all_users_streaks
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from routes.predict import router as PredictRouter
from routes.tracker import router as TrackerRouter
from routes.request import router as RequestRouter
app = FastAPI()
token_listener = JWTBearer()

# Initialize Prometheus metrics
instrumentator = Instrumentator()
instrumentator.instrument(app).expose(app)

def start_scheduler():
    try:
        scheduler = AsyncIOScheduler()
        scheduler.add_job(lambda: cron_notification.delay(), CronTrigger(second=0), id="cron_notification")
        scheduler.add_job(lambda: mark_not_done.delay(), CronTrigger(second=10), id="mark_not_done")
        scheduler.add_job(lambda: reset_sessions_status.delay(), CronTrigger(hour=0, minute=0), id="reset_sessions_status")
        scheduler.add_job(lambda: update_all_users_streaks.delay(), CronTrigger(hour=0, minute=0), id="update_all_users_streaks")
        scheduler.start()
    except Exception as e:
        print(f"Error starting scheduler: {e}")


@app.on_event("startup")
async def on_startup():
    start_scheduler()
    await initiate_database()

@app.get("/", tags=["Root"])
async def read_root():
    return {"message": "Welcome to this fantastic app."}

# Routes
app.include_router(MediaRouter, tags=["Media"], prefix="/v1/media")
app.include_router(AuthRouter, tags=["Authentication"], prefix="/v1/auth")
app.include_router(AdminRouter, tags=["Administrator"], prefix="/v1/admin")
app.include_router(RoutineRouter, tags=["Routines"], prefix="/v1/routine")
app.include_router(UserRouter, tags=["Users"], prefix="/v1/user", dependencies=[Depends(token_listener)])
app.include_router(PredictRouter, tags=["Predict"], prefix="/v1/predict",dependencies=[Depends(token_listener)])
app.include_router(TrackerRouter, tags=["Tracker"], prefix="/v1/tracker", dependencies=[Depends(token_listener)])
app.include_router(RequestRouter, tags=["Request"], prefix="/v1/request", dependencies=[Depends(token_listener)])
app.include_router(CoupleRouter, tags=["Couple"], prefix="/v1/couple", dependencies=[Depends(token_listener)])
app.include_router(GeminiRouter, tags=["Gemini"], prefix="/v1/gemini", dependencies=[Depends(token_listener)])
