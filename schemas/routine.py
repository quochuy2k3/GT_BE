from pydantic import BaseModel
from typing import List, Optional

from models.routine import Day


class StepSchema(BaseModel):
    step_order: int
    step_name: str

    class Config:
        json_schema_extra = {
            "example": {
                "step_order": 1,
                "step_name": "Cleanser"
            }
        }

class SessionSchema(BaseModel):
    time: str
    status: str
    steps: List[StepSchema]

    class Config:
        json_schema_extra = {
            "example": {
                "time": "08:00 AM",
                "steps": [{"step_order": 1, "step_name": "Cleanser"}]
            }
        }

class DaySchema(BaseModel):
    day_of_week: str
    sessions: Optional[List[SessionSchema]] = []
    class Config:
        json_schema_extra = {
            "example": {
                "day_of_week": "Monday",
                "sessions": [{"status": "pending","time": "08:00 AM", "steps": [{"step_order": 1, "step_name": "Cleanser"}]}]
            }
        }
class DayResponseSchema(BaseModel):
    routine_name: str
    push_token: Optional[str] = None
    today: DaySchema

class RoutineSchema(BaseModel):
    routine_name: str
    push_token: Optional[str] = None
    days: List[DaySchema]
    class Config:
        json_schema_extra = {
            "example": {
                "routine_name": "Morning Routine",
                "push_token": "ExponentPushToken[4nydRdM8BJ582YQ40-PiLm]",
                "days": [
                    {
                        "day_of_week": "Monday",
                        "sessions": [
                            {
                                "status": "done",
                                "steps": [
                                    {
                                        "step_name": "Cleanser",
                                        "step_order": 1
                                    }
                                ],
                                "time": "08:00 AM"
                            },
                            {
                                "status": "done",
                                "steps": [
                                    {
                                        "step_name": "Cleanser",
                                        "step_order": 1
                                    },
                                    {
                                        "step_name": "Toner",
                                        "step_order": 2
                                    }
                                ],
                                "time": "08:00 PM"
                            }
                        ]
                    },
                    {
                        "day_of_week": "Tuesday",
                        "sessions": []
                    },
                    {
                        "day_of_week": "Wednesday",
                        "sessions": []
                    },
                    {
                        "day_of_week": "Thursday",
                        "sessions": []
                    },
                    {
                        "day_of_week": "Friday",
                        "sessions": []
                    },
                    {
                        "day_of_week": "Saturday",
                        "sessions": []
                    },
                    {
                        "day_of_week": "Sunday",
                        "sessions": []
                    }
                ]
            }
        }



class RoutineUpdateSchema(BaseModel):
    routine_name: Optional[str] = None
    push_token: Optional[str] = None
    days: Optional[List[Day]] = None

class RoutineUpdatePushToken(BaseModel):
    push_token: Optional[str] = None

class RoutineNameUpdate(BaseModel):
    routine_name: str
