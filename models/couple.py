from typing import Optional, Any

from beanie import Document
from fastapi.security import HTTPBasicCredentials
from pydantic import BaseModel, EmailStr
from beanie import PydanticObjectId
from datetime import datetime
from pydantic import Field


class Couple(Document):
    user_1: PydanticObjectId
    user_2: PydanticObjectId
    streak: Optional[int] = 0
    created_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_1": "60d5ec9af3b76be4f42c5f90",
                "user_2": "60d5ec9af3b76be4f42c5f91",
                "streak": 0,
                "created_at": datetime.now()
            }
        }

    class Settings:
        name = "couple"

