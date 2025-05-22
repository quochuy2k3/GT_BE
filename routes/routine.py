from bson import ObjectId
from fastapi import APIRouter, HTTPException, Depends, Body
from typing import List
from beanie import PydanticObjectId
from datetime import datetime
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
            day.sessions = sorted(updated_day.sessions or [], key=lambda s: parse_time_string(s.time))
            await routine.save()
            print(day)
            return day

    raise HTTPException(status_code=404, detail="Day not found in routine")

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

    for day in routine.days:
        if day.day_of_week.lower() == day_of_week.lower():
            for session in day.sessions:
                if session.time == time:
                    if session.status != "done":
                        session.status = "done"
                        await routine.save()
                    return day

    raise HTTPException(status_code=404, detail="Session not found")

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
