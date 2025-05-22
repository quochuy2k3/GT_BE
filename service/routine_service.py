import asyncio
import httpx
import logging
from datetime import datetime, timedelta
from beanie import PydanticObjectId
from database.database import add_routine
from models.routine import Day, Routine
from database.celery_worker import celery_app
from config.config import initiate_database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def create_routine_for_new_user(user_id: PydanticObjectId):
    logger.info(f"Creating routine for new user: {user_id}")
    all_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    routine_days = [Day(day_of_week=day, sessions=[]) for day in all_days]

    routine = Routine(
        user_id=user_id,
        routine_name="Default Routine",
        days=routine_days
    )

    new_routine = await add_routine(routine)
    logger.info(f"New routine created: {new_routine.id}")
    return new_routine

async def get_routine_by_user_id(user_id: PydanticObjectId):
    return await Routine.find_one(Routine.user_id == user_id)

async def send_push_notification(push_token: str, title: str, subtitle: str, body: str):
    logger.info(f"Sending push notification to {push_token}")
    message = {
        "to": push_token,
        "sound": "default",
        "title": title,
        "body": body,
        "badge": 1,
    }
    url = "https://exp.host/--/api/v2/push/send"
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=message)
        if response.status_code == 200:
            logger.info(f"Notification sent successfully to {push_token}")
        else:
            logger.error(f"Failed to send notification to {push_token}: {response.text}")

async def check_and_send_routine_notifications(user_routine: Routine):
    current_day = datetime.now().strftime('%A')
    current_time = datetime.now().strftime('%I:%M %p').strip()
    if not user_routine.push_token:
        return
    for day in user_routine.days:
        if day.day_of_week == current_day:
            for session in day.sessions:
                if session.time.strip() == current_time:
                    title = "Time for skincare"
                    body = f"You have {len(session.steps)} steps in your skincare routine at {session.time.strip()}."
                    await send_push_notification(user_routine.push_token, title, "", body)

async def real_mark_not_done(batch_size=100):
    # Initialize database connection first
    await initiate_database()
    
    logger.info("Marking sessions as 'not_done' if applicable...")
    skip = 0
    while True:
        routines = await Routine.find_all().skip(skip).limit(batch_size).to_list()
        if not routines:
            break
        tasks = [process_routine(routine) for routine in routines]
        await asyncio.gather(*tasks)
        skip += batch_size
    logger.info("Marking process completed.")


async def process_routine(routine: Routine):
    current_day = datetime.now().strftime('%A').lower()
    current_time = datetime.now().strftime('%I:%M %p').strip()

    logger.info(f"Processing routine for today: {current_day}, current time: {current_time}")

    for day in routine.days:
        if day.day_of_week.lower() == current_day:
            logger.info(f"Found routine for today: {current_day}")

            for session in day.sessions:
                if not session.steps:
                    session.status = 'not_done'
                    logger.info(f"Session has no steps, marked as 'not_done' for routine {routine.id}")
                    continue

                session_time = datetime.strptime(session.time.strip(), '%I:%M %p')
                current_time_obj = datetime.strptime(current_time, '%I:%M %p')

                if session_time < (current_time_obj - timedelta(hours=1)) and session.status == 'pending':
                    logger.info(f"Session {session_time} is more than 1 hour old and still pending, marking as 'not_done'")
                    session.status = 'not_done'

            if any(session.status == 'not_done' for session in day.sessions):
                await routine.update({"$set": {"days": routine.days}})
                logger.info(f"Routine {routine.id} updated with new session status.")
            break

async def real_reset_sessions_status(batch_size=100):
    # Initialize database connection first
    await initiate_database()
    
    current_time = datetime.now()
    if current_time.hour == 0 and current_time.minute == 0:
        logger.info("Resetting all session statuses to 'pending'...")
        skip = 0
        while True:
            routines = await Routine.find_all().skip(skip).limit(batch_size).to_list()
            if not routines:
                break
            tasks = [update_routine_sessions(routine) for routine in routines]
            await asyncio.gather(*tasks)
            skip += batch_size
        logger.info("Session statuses reset completed.")
    else:
        logger.info("Not the right time for session reset.")


async def update_routine_sessions(routine: Routine):
    for day in routine.days:
        for session in day.sessions:
            session.status = "pending"
    await routine.update({"$set": {"days": routine.days}})
    logger.info(f"Routine {routine.id} session statuses reset to 'pending'.")

async def real_cron_notification(batch_size=100):
    # Initialize database connection first
    await initiate_database()
    
    logger.info("Cron job is running...")
    skip = 0
    while True:
        routines = await Routine.find_all().skip(skip).limit(batch_size).to_list()
        if not routines:
            break
        tasks = [check_and_send_routine_notifications(routine) for routine in routines]
        await asyncio.gather(*tasks)
        skip += batch_size

@celery_app.task(bind=True)
def cron_notification(self):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(real_cron_notification())
    finally:
        loop.close()

@celery_app.task(bind=True)
def mark_not_done(self):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(real_mark_not_done())
    finally:
        loop.close()

@celery_app.task(bind=True)
def reset_sessions_status(self):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(real_reset_sessions_status())
    finally:
        loop.close()