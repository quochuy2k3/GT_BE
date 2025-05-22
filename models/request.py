from typing import Optional, Any

from beanie import Document
from fastapi.security import HTTPBasicCredentials
from pydantic import BaseModel, EmailStr
from beanie import PydanticObjectId
from datetime import datetime
from pydantic import Field
from enum import Enum
class StatusEnum(str, Enum):
    pending = "pending"
    accepted = "accepted"

class Request(Document):
    user_id: PydanticObjectId
    partner_id: PydanticObjectId
    status: StatusEnum = StatusEnum.pending
    created_at: datetime = Field(default_factory=datetime.now)
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "Test user",
                "partner_id": "abdul@school.com",
                "status": StatusEnum.pending,
                "created_at": datetime.now()
            }
        }

    class Settings:
        name = "request"

