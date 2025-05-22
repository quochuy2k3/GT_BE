from pydantic import BaseModel, Field, EmailStr
from beanie import PydanticObjectId
from enum import Enum
from datetime import datetime
from typing import List, Optional, Dict, Any

class StatusEnum(str, Enum):
    pending = "pending"
    accepted = "accepted"


class CreateRequestSchema(BaseModel):
    email: EmailStr

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com"
            }
        }


class UserInfoSchema(BaseModel):
    fullname: Optional[str] = None
    email: EmailStr
    avatar: Optional[str] = None


class RequestSchema(BaseModel):
    user_id: PydanticObjectId
    partner_id: PydanticObjectId
    status: StatusEnum = StatusEnum.pending
    created_at: datetime = Field(default_factory=datetime.now)


class ListRequestSchema(BaseModel):
    requests: List[RequestSchema]


class RequestResponseSchema(BaseModel):
    id: Optional[PydanticObjectId] = None
    user_id: PydanticObjectId
    partner_id: PydanticObjectId
    status: StatusEnum
    created_at: datetime
    message: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": "60d5ec9af3b76be4f42c5f92",
                "user_id": "60d5ec9af3b76be4f42c5f90",
                "partner_id": "60d5ec9af3b76be4f42c5f91",
                "status": "pending",
                "created_at": "2023-01-01T00:00:00.000Z",
                "message": "Friend request sent successfully"
            }
        }


class ReceivedRequestSchema(BaseModel):
    id: PydanticObjectId
    user_id: PydanticObjectId
    partner_id: PydanticObjectId
    status: StatusEnum
    created_at: datetime
    sender_info: Optional[UserInfoSchema] = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": "60d5ec9af3b76be4f42c5f92",
                "user_id": "60d5ec9af3b76be4f42c5f90",
                "partner_id": "60d5ec9af3b76be4f42c5f91",
                "status": "pending",
                "created_at": "2023-01-01T00:00:00.000Z",
                "sender_info": {
                    "fullname": "John Doe",
                    "email": "john@example.com",
                    "avatar": "https://example.com/avatar.jpg"
                }
            }
        }


class SentRequestSchema(BaseModel):
    id: PydanticObjectId
    user_id: PydanticObjectId
    partner_id: PydanticObjectId
    status: StatusEnum
    created_at: datetime
    receiver_info: Optional[UserInfoSchema] = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": "60d5ec9af3b76be4f42c5f92",
                "user_id": "60d5ec9af3b76be4f42c5f90",
                "partner_id": "60d5ec9af3b76be4f42c5f91",
                "status": "pending",
                "created_at": "2023-01-01T00:00:00.000Z",
                "receiver_info": {
                    "fullname": "Jane Doe",
                    "email": "jane@example.com",
                    "avatar": "https://example.com/avatar2.jpg"
                }
            }
        }

