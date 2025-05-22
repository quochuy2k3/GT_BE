from beanie import PydanticObjectId
from bson import ObjectId

from database.database import add_tracker
from models.tracker import Tracker, ClassEnum
from datetime import datetime
import os
import uuid
from config.jwt_handler import decode_jwt
from fastapi import Depends 
from models.routine import Day, Routine
from schemas.routine import DaySchema
from routes.media import upload_scan_image_to_cloudinary
from routes.routine import serialize_day
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from beanie import PydanticObjectId
from models.user import User
import asyncio
from database.celery_worker import celery_app
from config.config import initiate_database

async def tracker_on_day(token: str, image_data: bytes, class_summary: dict):
    """
    Background task to save tracking data after skin condition detection.
    Checks if user already has a tracker for today and updates it instead of creating new.

    Args:
        token: JWT token for user authentication
        image_data: Image bytes to be stored
        class_summary: Summary of detected skin conditions
    """
    try:
        # Extract user ID from JWT token
        token_data = decode_jwt(token)
        user_id = token_data.get("sub")

        if not user_id:
            print("Error: Unable to extract user_id from token")
            return
        user_id = PydanticObjectId(user_id)  # Convert to PydanticObjectId

        # Upload image to Cloudinary
        img_url = await upload_scan_image_to_cloudinary(image_data)
        print(img_url)
        if "Error" in img_url:
            print(f"Error: {img_url}")
            return

        # Find user's routine
        routine = await Routine.find_one(Routine.user_id == user_id)

        if not routine:
            print(f"Warning: No routine found for user {user_id}")
            day_routine = None
        else:
            # Get current day's routine
            today_name = datetime.now().strftime("%A").lower()
            day_routine = None

            for day in routine.days:
                if day.day_of_week.lower() == today_name:
                    today_data = serialize_day(day)
                    day_routine = DaySchema.model_validate(today_data)
                    break

            if not day_routine:
                print(f"Warning: No routine found for today ({today_name}) for user {user_id}")

        today = datetime.now().date()
        time_tracking = datetime.now().strftime("%H:%M")
        existing_tracker = await Tracker.find_one({
            "user_id": ObjectId(str(user_id)),
            "date": today
        })

        if existing_tracker:
            existing_tracker.routine_of_day = day_routine
            existing_tracker.img_url = img_url
            existing_tracker.class_summary = class_summary
            existing_tracker.timeTracking = time_tracking
            await existing_tracker.save()
        else:
        # Create new tracker document
            tracker = Tracker(
                user_id=user_id,
                routine_of_day=day_routine,
                img_url=img_url,
                class_summary=class_summary,
                date=today,
                timeTracking=time_tracking
            )
            await add_tracker(tracker)
            await update_user_streak(user_id)
    except Exception as e:
        print(f"Error in tracker_on_day: {str(e)}")

async def update_user_streak(user_id: PydanticObjectId) -> int:
 
    today = datetime.now().date()
    
    trackers = await Tracker.find(
        {"user_id": user_id},
        projection_model=Tracker
    ).sort([("date", 1)]).to_list()

    if not trackers:
        await User.find_one(User.id == user_id).update({"$set": {"streak": 0}})
        return 0

    tracked_dates = [t.date for t in trackers]
    streak = 0
    current_date = today
    allow_skip_today = True

    for i in range(len(tracked_dates) - 1, -1, -1):
        tracked_date = tracked_dates[i]

        if tracked_date == current_date:
            streak += 1
            current_date -= timedelta(days=1)
        elif tracked_date < current_date:
            if allow_skip_today and current_date == today:
                allow_skip_today = False
                current_date -= timedelta(days=1)
                if tracked_date == current_date:
                    streak += 1
                    current_date -= timedelta(days=1)
                else:
                    break
            else:
                break
        else:
            continue

    await User.find_one(User.id == user_id).update({"$set": {"streak": streak}})
    return streak

async def real_update_all_users_streaks(batch_size=100):
    """
    Updates streak counts for all users. This function is designed to be run
    daily at midnight to ensure all users have accurate streak counts.
    
    Args:
        batch_size (int): Number of users to process in each batch
    """
    # Initialize database connection first
    await initiate_database()
    
    print("Daily streak update job is running...")
    skip = 0
    
    while True:
        # Get users in batches to avoid memory issues with large user bases
        users = await User.find().skip(skip).limit(batch_size).to_list()
        
        if not users:
            break  # No more users to process
            
        # Process users in parallel for efficiency
        tasks = []
        for user in users:
            tasks.append(update_user_streak(user.id))
            
        # Wait for all streak updates in this batch to complete
        await asyncio.gather(*tasks)
        
        skip += batch_size
        
    print(f"Daily streak update completed for all users")

@celery_app.task(bind=True)
def update_all_users_streaks(self):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(real_update_all_users_streaks())
    finally:
        loop.close()