from typing import Optional
from beanie import PydanticObjectId
from models.admin import Admin
from models.tracker import Tracker
from models.user import User
from models.routine import Routine
from models.request import Request
from pydantic import BaseModel


admin_collection = Admin
user_collection = User
routine_collection = Routine
tracker_collection = Tracker
request_collection = Request

# Thêm người dùng mới
async def add_admin(new_admin: Admin) -> Admin:
    admin = await new_admin.create()
    return admin

async def add_user(new_user: User) -> User:
    user = await new_user.create()
    return user

async def add_tracker(new_tracker: Tracker) -> Tracker:
    tracker = await new_tracker.create()
    return tracker

async def add_routine(new_routine: Routine) -> Routine:
    routine = await new_routine.create()
    return routine

async def add_request(new_request: Request) -> Request:
    request = await new_request.create()
    return request

async def update_user_data(id: PydanticObjectId, data: dict) -> Optional[User]:
    des_body = {k: v for k, v in data.items() if v is not None}
    
    if not des_body:
        raise ValueError("No valid fields to update.")
    
    update_query = {"$set": {field: value for field, value in des_body.items()}}
    
    user = await user_collection.get(id)
    if not user:
        raise ValueError(f"User with ID {id} not found.")
    await user.update(update_query)
    return user


# Đảm bảo bạn xử lý các lỗi như không tìm thấy người dùng hoặ không có dữ liệu hợp lệ
