from beanie import Document, PydanticObjectId
from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum

class StatusEnum(str, Enum):
    pending = "pending"
    done = "done"
    not_done = "not_done"

# Step cho mỗi session
class Step(BaseModel):
    step_order: int
    step_name: str

# Session cho mỗi ngày
class Session(BaseModel):
    status: StatusEnum = StatusEnum.pending
    time: str
    steps: List[Step]

# Day cho mỗi ngày trong tuần
class Day(BaseModel):
    day_of_week: str
    sessions: List[Session]
class Routine(Document):
    user_id: PydanticObjectId
    routine_name: Optional[str] = None
    push_token: Optional[str] = None  # Make this field optional
    days: List[Day] = [
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

    class Settings:
        name = "routine"  # Đặt tên collection MongoDB là "routine"

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
