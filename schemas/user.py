from fastapi.security import HTTPBasicCredentials
from pydantic import BaseModel, EmailStr
from typing import Optional, Any

from schemas.routine import RoutineSchema



class UserSignIn(BaseModel):
    email: str
    password: str

    class Config:
        json_schema_extra = {
            "example": {"email": "test123@gmail.com", "password": "password"}
        }


class UpdateUserModel(BaseModel):
    fullname: Optional[str]
    email: Optional[EmailStr]
    phone: Optional[str]
    password: Optional[str]
    genders: Optional[str]
    role: Optional[str]

    class Config:
        json_schema_extra = {
            "example": {
                "fullname": "Vo Quoc Huy",
                "email": "test@gmail.com",
                "phone": "0123456789",
                "genders": "male",
                "password": "password",
                "role": "baseUser",
            }
        }

class Response(BaseModel):
    status_code: int
    response_type: str
    description: str
    data: Optional[Any]

    class Config:
        json_schema_extra = {
            "example": {
                "status_code": 200,
                "response_type": "success",
                "description": "Operation successful",
                "data": "Sample data",
            }
        }
class UserData(BaseModel):
    fullname: Optional[str]
    email: EmailStr
    phone: Optional[str]
    gender: Optional[str]
    role: Optional[str]
    avatar: Optional[str]
    streak: Optional[int]
    push_token: Optional[str]
    class Config:
        json_schema_extra = {
            "example": {
                "fullname": "Vo Quoc Huy",
                "email": "test@gmail.com",
                "phone": "0123456789",
                "gender": "male",
                "role": "baseUser",
                "avatar": "https://i.ibb.co/cN0nmSj/Screenshot-2023-06-23-at-01-11-12.png",
                "streak": 0,
                "push_token": "1234567890"
            }
        }

class UserSignUp(BaseModel):
    fullname: Optional[str]
    email: EmailStr
    password: Optional[str]
    phone: Optional[str]
    gender: Optional[str]
    avatar: Optional[str]

    class Config:
        json_schema_extra = {
            "example": {
                "fullname": "Vo Quoc Huy",
                "password": "password",
                "email": "test@gmail.com",
                "phone": "0123456789",
                "gender": "male",
                "avatar": "https://i.ibb.co/cN0nmSj/Screenshot-2023-06-23-at-01-11-12.png",
            }
        }