from datetime import datetime, timedelta
from typing import List

from beanie import PydanticObjectId
from bson import ObjectId
from fastapi import APIRouter, Body, HTTPException, Depends
from fastapi import Query

from config.jwt_bearer import JWTBearer
from config.jwt_handler import sign_jwt, decode_jwt
from models import Tracker
from schemas.tracker import DayStatus, TrackerSummary
from schemas.user import UserData
from service.user_service import get_current_user
from service.tracker_service import update_user_streak
from models import User
router = APIRouter()


@router.get("", response_model=UserData)
async def detail_user(token: str = Depends(JWTBearer())):
    payload = decode_jwt(token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid token: user_id not found")

    user_data = await get_current_user(user_id)
    print(user_data)
    return user_data


@router.get("/latest")
async def get_latest_tracker(token: str = Depends(JWTBearer())):
    """
    API to get the most recent tracker entry for the authenticated user.

    Args:
        token: JWT token for user authentication.

    Returns:
        The most recent tracker entry for the user.
    """
    try:
        # Extract user ID from JWT token
        token_data = decode_jwt(token)
        user_id = token_data.get("sub")

        if not user_id:
            raise HTTPException(status_code=400, detail="Invalid token, unable to extract user_id")

        user_id = PydanticObjectId(user_id)  # Convert to PydanticObjectId

        # Find the most recent tracker for the user, sorted by date descending
        latest_tracker = await Tracker.find_one(
            {"user_id": user_id},
            sort=[("date", -1)]  # Sort by date in descending order
        )

        if not latest_tracker:
            raise HTTPException(status_code=404, detail="No tracker found for the user")

        return latest_tracker

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


# Hàm lấy tất cả các ngày trong tuần này (từ thứ 2 đến chủ nhật)
def get_dates_of_current_week():
    today = datetime.utcnow()  # Điều chỉnh giờ theo UTC+7
    start_of_week = today - timedelta(days=today.weekday())  # Tính ngày thứ 2 của tuần này
    dates = [start_of_week + timedelta(days=i) for i in range(7)]  # Tạo danh sách các ngày trong tuần
    return dates

@router.get("/week-status", response_model=List[DayStatus])
async def get_week_status(token: str = Depends(JWTBearer())):
    try:
        # Extract user ID from JWT token
        token_data = decode_jwt(token)
        user_id = token_data.get("sub")
        user_id = PydanticObjectId(user_id)
        if not user_id:
            raise HTTPException(status_code=400, detail="Invalid token, unable to extract user_id")

        # Lấy danh sách các ngày trong tuần
        dates = get_dates_of_current_week()
        result = []

        for date in dates:
            date_str = date.strftime("%Y-%m-%d")


            start_of_day = datetime(date.year, date.month, date.day)
            end_of_day = start_of_day + timedelta(days=1)  # 23:59:59 UTC+7

            trackers = await Tracker.find({
                    "user_id": user_id,
                    "date": {"$gte": start_of_day, "$lt": end_of_day}
                }).to_list()

            if trackers:
                tracker_ids = [str(tracker.id) for tracker in trackers]  # Lấy các tracker_id và chuyển thành chuỗi
                result.append(DayStatus(date=date_str, isHasValue=True, tracker_id=tracker_ids))
            else:
                result.append(DayStatus(date=date_str, isHasValue=False))

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@router.get("/{tracker_id}", response_model=Tracker)
async def get_tracker_by_id(tracker_id: str, token: str = Depends(JWTBearer())):
    try:
        # Extract user ID from JWT token
        token_data = decode_jwt(token)
        user_id = token_data.get("sub")

        if not user_id:
            raise HTTPException(status_code=400, detail="Invalid token, unable to extract user_id")

        user_id = PydanticObjectId(user_id)

        tracker = await Tracker.find_one({"_id": PydanticObjectId(tracker_id), "user_id": user_id})

        if not tracker:
            raise HTTPException(status_code=404, detail="Tracker not found")

        return tracker

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
    
@router.get("/trackers/by-date-range", response_model=List[TrackerSummary])
async def get_trackers_by_date_range(
    start_date: str = Query(..., example="2024-01-01"),
    end_date: str = Query(..., example="2024-01-31"),
    token: str = Depends(JWTBearer())
):
    """
    Get list of trackers between start_date and end_date (inclusive).
    - Format: YYYY-MM-DD
    """
    try:
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
            end = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

        if start > end:
            raise HTTPException(status_code=400, detail="start_date must be before or equal to end_date")

        # Get user_id from token
        token_data = decode_jwt(token)
        user_id = token_data.get("sub")
        if not user_id:
            raise HTTPException(status_code=400, detail="Invalid token")

        user_id = PydanticObjectId(user_id)

        # Find trackers in date range
        trackers = await Tracker.find({
            "user_id": user_id,
            "date": {"$gte": start, "$lte": end}
        }).sort([("date", -1)]).to_list()

        # Format output
        response = [
            TrackerSummary(
                id=str(tracker.id),
                date=tracker.date.isoformat(),
                time=tracker.timeTracking,
                img=tracker.img_url
            )
            for tracker in trackers
        ]

        return response

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Internal error: {str(e)}")
    

@router.post("/update-user-streak")
async def update_user_streak(token: str = Depends(JWTBearer())) -> int:
    token_data = decode_jwt(token)
    user_id = token_data.get("sub")
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid token")
    user_id = PydanticObjectId(user_id)
    
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