from fastapi.security import HTTPBasicCredentials
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Any, List, Dict
from beanie import PydanticObjectId
from datetime import datetime

from schemas.routine import DaySchema


class CreateCoupleSchema(BaseModel):
    user_1: PydanticObjectId
    user_2: PydanticObjectId


class CoupleResponse(BaseModel):
    id: str
    user_1: str
    user_2: str
    created_at: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": "60d5ec9af3b76be4f42c5f92",
                "user_1": "60d5ec9af3b76be4f42c5f90",
                "user_2": "60d5ec9af3b76be4f42c5f91",
                "created_at": "2023-01-01T00:00:00.000Z"
            }
        }


class UserBasicInfo(BaseModel):
    id: str
    fullname: str
    email: str
    avatar: Optional[str] = None
    streak: Optional[int] = 0


class TodayTrackerSchema(BaseModel):
    id: str
    user_id: str
    img_url: Optional[str] = None
    date: str
    class_summary: Optional[Dict[str, Any]] = None
    timeTracking: Optional[str] = None


class PartnerRoutineSchema(BaseModel):
    routine_name: str
    day_of_week: str
    sessions: list


class PartnerInfoSchema(BaseModel):
    id: str
    fullname: str
    email: str
    avatar: Optional[str] = None
    streak: int
    today_tracker: Optional[TodayTrackerSchema] = None
    routine: Optional[PartnerRoutineSchema] = None


class CoupleDetailResponse(BaseModel):
    id: str
    created_at: datetime
    partner: PartnerInfoSchema

    class Config:
        json_schema_extra = {
            "example": {
                "id": "60d5ec9af3b76be4f42c5f92",
                "created_at": "2023-01-01T00:00:00.000Z",
                "partner": {
                    "id": "60d5ec9af3b76be4f42c5f91",
                    "fullname": "Jane Doe",
                    "email": "jane@example.com",
                    "avatar": "https://example.com/avatar.jpg",
                    "streak": 5,
                    "today_tracker": {
                        "id": "60d5ec9af3b76be4f42c5f94",
                        "user_id": "60d5ec9af3b76be4f42c5f91",
                        "img_url": "https://example.com/image.jpg",
                        "date": "2023-01-01"
                    },
                    "routine": {
                        "routine_name": "Evening Routine",
                        "day_of_week": "Monday",
                        "sessions": [
                          {
                            "status": "pending",
                            "time": "08:00 PM",
                            "steps": [
                              {
                                "step_order": 1,
                                "step_name": "Cleanser"
                              },
                              {
                                "step_order": 2,
                                "step_name": "Toner"
                              }
                            ]
                          }
                        ]
                    }
                }
            }
        }


class CoupleReminderSchema(BaseModel):
    partner_id: str
    push_token: str
