from fastapi import HTTPException
from beanie import PydanticObjectId
from bson import ObjectId
from models.user import User
from service.routine_service import get_routine_by_user_id

async def get_current_user(user_id: PydanticObjectId):
    try:
        # Chuyển user_id thành ObjectId nếu cần
        user_id = ObjectId(user_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid user_id format")

    # Lấy thông tin người dùng từ MongoDB
    user = await User.find_one({"_id": user_id})
    # Lấy routine của người dùng
    routine = await get_routine_by_user_id(user_id)

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if routine is None:
        raise HTTPException(status_code=404, detail="Routine not found")

    # Trả về thông tin người dùng và routine trong một dictionary
    return {
        "fullname": user.fullname,
        "email": user.email,
        "phone": user.phone,
        "gender": user.gender,
        "role": user.role,
        "avatar": user.avatar,
        "streak": user.streak,
        "push_token": user.push_token
    }

async def update_push_token_user(user_id: PydanticObjectId, push_token: str):
    user = await User.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.push_token = push_token
    await user.save()
    print(f"Updated push token: {user.push_token}")
    return {"message": "Push token updated successfully"}   
