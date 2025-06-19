from bson import ObjectId
from fastapi import APIRouter, HTTPException, Depends, Body
from typing import List
from beanie import PydanticObjectId
from datetime import datetime, timezone, timedelta
from monitoring.fastapi_metrics import increment_routine_completion
from config.jwt_bearer import JWTBearer
from config.jwt_handler import decode_jwt
from models.routine import Routine, Day
from schemas.routine import RoutineSchema, SessionSchema, DaySchema, DayResponseSchema, RoutineUpdateSchema, \
    RoutineUpdatePushToken, RoutineNameUpdate
from service.routine_service import cron_notification, process_routine
from service.user_service import update_push_token_user
router = APIRouter()


@router.get("/", response_model=RoutineSchema)
async def get_detail_routine(token: str = Depends(JWTBearer())):
    payload = decode_jwt(token)
    user_id = payload.get("sub")

    try:
        user_id = ObjectId(user_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid user_id format")

    routine = await Routine.find_one(Routine.user_id == user_id)

    if routine is None:
        raise HTTPException(status_code=404, detail="Routine not found")

    return routine

@router.put("/", response_model=RoutineSchema)
async def update_routine(routine: RoutineSchema, token: str = Depends(JWTBearer())):
    payload = decode_jwt(token)
    user_id = payload.get("sub")
    print(routine.days[0].sessions[0].status)
    print(routine)
    try:
        user_id = ObjectId(user_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid user_id format")

    existing_routine = await Routine.find_one({"user_id": user_id})
    if not existing_routine:
        raise HTTPException(status_code=404, detail="Routine not found")

    existing_routine.routine_name = routine.routine_name
    existing_routine.push_token = routine.push_token
    existing_routine.days = routine.days

    await existing_routine.save()
    return existing_routine


@router.post("/cron", )
async def test_routine():
    await cron_notification()
    return HTTPException(status_code=200, detail="Routine test successfully")



def parse_time_string(time_str: str) -> datetime:
    return datetime.strptime(time_str, "%I:%M %p")

def is_past_time_utc7(time_str: str) -> bool:
    """Check if the given time is in the past in UTC+7 timezone"""
    try:
        # Get current time in UTC+7
        utc7_tz = timezone(timedelta(hours=7))
        now_utc7 = datetime.now(utc7_tz)
        
        # Parse the session time and set it to today's date in UTC+7
        session_time = datetime.strptime(time_str, "%I:%M %p")
        today_session_time = now_utc7.replace(
            hour=session_time.hour, 
            minute=session_time.minute, 
            second=0, 
            microsecond=0
        )
        
        return today_session_time < now_utc7
    except:
        return False

@router.put("/update-day", response_model=DaySchema)
async def update_sessions_for_day(
    updated_day: DaySchema = Body(...),
    token: str = Depends(JWTBearer())
):

    payload = decode_jwt(token)
    user_id = payload.get("sub")

    try:
        user_id = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user_id format")

    routine = await Routine.find_one(Routine.user_id == user_id)
    if not routine:
        raise HTTPException(status_code=404, detail="Routine not found")

    for day in routine.days:
        if day.day_of_week.lower() == updated_day.day_of_week.lower():
            # Store old sessions for comparison
            old_sessions = {session.time: session.status for session in day.sessions or []}
            
            # Process new sessions
            processed_sessions = []
            for new_session in updated_day.sessions or []:
                # Priority 1: If request explicitly sends "done" status, keep it
                if new_session.status == "done":
                    # Keep the "done" status from request
                    pass
                # Priority 2: If session time exists in old sessions, preserve the old status
                elif new_session.time in old_sessions:
                    new_session.status = old_sessions[new_session.time]
                # Priority 3: If this is a new session and the time is in the past, set status to "not_done"
                elif is_past_time_utc7(new_session.time):
                    new_session.status = "not_done"
                # Priority 4: Otherwise keep the status from the new session data
                
                processed_sessions.append(new_session)
                
                # Debug log
                print(f"Session {new_session.time}: final status = {new_session.status}")
            
            # Sort sessions by time and update
            day.sessions = sorted(processed_sessions, key=lambda s: parse_time_string(s.time))
            await routine.save()
            print(f"Updated day: {day}")
            return day

    raise HTTPException(status_code=404, detail="Day not found in routine")

def is_within_deadline_utc7(session_time_str: str) -> bool:
    """Check if current time is within 1 hour after the session time in UTC+7 timezone"""
    try:
        utc7_tz = timezone(timedelta(hours=7))
        now_utc7 = datetime.now(utc7_tz)
        
        session_time_str_normalized = session_time_str.upper()
        
        session_time = None
        for time_format in ["%I:%M %p", "%H:%M"]:
            try:
                session_time = datetime.strptime(session_time_str_normalized, time_format)
                break
            except ValueError:
                continue
        
        if session_time is None:
            print(f"Could not parse time format: {session_time_str}")
            return False
        
        # Set session time to today's date in UTC+7
        today_session_time = now_utc7.replace(
            hour=session_time.hour, 
            minute=session_time.minute, 
            second=0, 
            microsecond=0
        )
        
        # Calculate deadline (1 hour after session time)
        deadline = today_session_time + timedelta(hours=1)
        
        # Debug logs
        print(f"Current time (UTC+7): {now_utc7}")
        print(f"Session time: {today_session_time}")
        print(f"Deadline: {deadline}")
        print(f"Is within deadline: {today_session_time <= now_utc7 <= deadline}")
        
        # Check if current time is between session time and deadline
        return today_session_time <= now_utc7 <= deadline
    except Exception as e:
        print(f"Error in is_within_deadline_utc7: {e}")
        return False

@router.put("/session/mark-done", response_model=DaySchema)
async def mark_session_done(
    day_of_week: str = Body(...),
    time: str = Body(...),
    token: str = Depends(JWTBearer())
):
    payload = decode_jwt(token)
    user_id = payload.get("sub")

    try:
        user_id = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user_id format")

    routine = await Routine.find_one(Routine.user_id == user_id)
    if not routine:
        raise HTTPException(status_code=404, detail="Routine not found")

    # Debug: Print the time being checked
    print(f"Attempting to mark done - Day: {day_of_week}, Time: {time}")
    
    # Check if current time is within deadline (1 hour after session time)
    # Temporarily disabled for debugging
    if not is_within_deadline_utc7(time):
        # For debugging, let's see what times we're working with but allow it anyway
        print(f"WARNING: Outside deadline but allowing for debug - Time: {time}")
        # Uncomment the line below to re-enable deadline checking
        # raise HTTPException(
        #     status_code=400, 
        #     detail=f"Cannot mark session as done. Deadline has passed (1 hour after session time). Current session time: {time}"
        # )

    for day in routine.days:
        if day.day_of_week.lower() == day_of_week.lower():
            for session in day.sessions:
                if session.time == time:
                    if session.status != "done":
                        session.status = "done"
                        await routine.save()
                        increment_routine_completion()  # Increment routine completion counter
                    return day

    raise HTTPException(status_code=404, detail=f"Session not found - Day: {day_of_week}, Time: {time}")

def serialize_day(day: Day) -> dict:
    return {
        "day_of_week": day.day_of_week,
        "sessions": [
            {
                "time": session.time,
                "status": session.status,
                "steps": [
                    {
                        "step_order": step.step_order,
                        "step_name": step.step_name,
                    } for step in session.steps
                ]
            } for session in day.sessions
        ]
    }
@router.get("/today", response_model=DayResponseSchema)
async def get_today_day(token: str = Depends(JWTBearer())):
    payload = decode_jwt(token)
    user_id = payload.get("sub")

    try:
        user_id = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user_id format")

    routine = await Routine.find_one(Routine.user_id == user_id)
    if not routine:
        raise HTTPException(status_code=404, detail="Routine not found")

    today_name = datetime.now().strftime("%A").lower()

    for day in routine.days:
        if day.day_of_week.lower() == today_name:
            today_data = serialize_day(day)
            return DayResponseSchema(
                routine_name=routine.routine_name,
                push_token=routine.push_token,
                today=DaySchema.model_validate(today_data)
            )

    raise HTTPException(status_code=404, detail="Today's routine not found")

@router.patch("/", response_model=RoutineSchema)
async def patch_routine(
    data: RoutineUpdateSchema = Body(...),
    token: str = Depends(JWTBearer())
):
    payload = decode_jwt(token)
    user_id = payload.get("sub")

    try:
        user_id = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user_id format")

    routine = await Routine.find_one(Routine.user_id == user_id)
    if not routine:
        raise HTTPException(status_code=404, detail="Routine not found")

    update_data = data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(routine, key, value)

    await routine.save()
    return routine

@router.patch("/update-push-token", response_description="Update push token" )
async def update_push_token(
    data : RoutineUpdatePushToken = Body(...),
    token: str = Depends(JWTBearer())
):
    payload = decode_jwt(token)
    user_id = payload.get("sub")

    try:
        user_id = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user_id format")

    # Tìm routine của user theo user_id
    routine = await Routine.find_one(Routine.user_id == user_id)
    if not routine:
        raise HTTPException(status_code=404, detail="Routine not found")

    # Cập nhật giá trị push_token
    print(data)
    routine.push_token = data.push_token
    # Lưu lại thay đổi vào cơ sở dữ liệu
    await routine.save()
    await update_push_token_user(user_id, data.push_token)

    # Trả về phản hồi thành công với status code 200
    return {"status": 200, "message": "Push token updated successfully"}


@router.patch("/update-routine-name")
async def update_routine_name(
    data: RoutineNameUpdate = Body(...),
    token: str = Depends(JWTBearer())
):
    payload = decode_jwt(token)
    user_id = payload.get("sub")

    try:
        user_id = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user_id format")

    routine = await Routine.find_one(Routine.user_id == user_id)
    if not routine:
        raise HTTPException(status_code=404, detail="Routine not found")

    routine.routine_name = data.routine_name
    await routine.save()

    return {"status": 200, "message": "Push token updated successfully"}


@router.get("/routine-in-time")
async def get_routine_in_time(token: str = Depends(JWTBearer())):
    payload = decode_jwt(token)
    user_id = payload.get("sub")
    user_id = ObjectId(user_id)
    routine = await Routine.find_one(Routine.user_id == user_id)
    if not routine:
        raise HTTPException(status_code=404, detail="Routine not found")

    await process_routine(routine)
    return {"status": 200, "message": "Routine processed successfully"}
