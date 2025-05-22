from beanie import Document, PydanticObjectId
from typing import List, Optional
from enum import Enum
from schemas.routine import DaySchema
from datetime import datetime, date

class ClassEnum(str, Enum):
    blackhead = "blackhead"
    papular = "papular"
    purulent = "purulent"


class Tracker(Document):
    user_id: PydanticObjectId
    routine_of_day: Optional[DaySchema] = None
    img_url: Optional[str] = None  
    class_summary: Optional[dict] = None
    date: date
    timeTracking: Optional[str] = None

    class Settings:
        name = "tracker"  # Đặt tên collection MongoDB là "routine"

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "1234567890",
                "routine_of_day": {
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
                "img_url": "https://example.com/image.jpg",
                "class_summary": {"blackhead": {"count": 1, "color": "#1E2761"}, "papular": {"count": 2, "color": "#FF5722"}, "purulent": {"count": 3, "color": "#FFEB3B"}},
                "date": date.today(),
                "timeTracking": "14:00"
            }
        }