from typing import Optional, Any

from beanie import Document
from fastapi.security import HTTPBasicCredentials
from pydantic import BaseModel, EmailStr


class User(Document):
    fullname: Optional[str]
    email: EmailStr
    phone: Optional[str]
    password: Optional[str]
    role: Optional[str]
    gender: Optional[str] = None
    avatar: Optional[str] = None
    streak: Optional[int] = 0
    push_token: Optional[str] = None
    class Config:
        json_schema_extra = {
            "example": {
                "fullname": "Test user",
                "email": "abdul@school.com",
                "phone": "0123456789",
                "password": "password",
                "gender": "male",
                "role": "baseUser",
                "streak": 0,
                "push_token": "push_token"
            }
        }

    class Settings:
        name = "user"

