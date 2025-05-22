from bson import ObjectId
from fastapi import APIRouter, Body, HTTPException, Depends


from config.jwt_bearer import JWTBearer
from config.jwt_handler import sign_jwt, decode_jwt
from schemas.user import UserData
from models.user import User
from service.user_service import get_current_user, update_push_token_user

router = APIRouter()


@router.get("", response_model=UserData)
async def detail_user(token: str = Depends(JWTBearer())):
    payload = decode_jwt(token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid token: user_id not found")

    user_data = await get_current_user(user_id)
    print(user_data)
    return user_data

@router.patch("/push-token")
async def update_push_token(token: str = Depends(JWTBearer()), push_token: str = Body(...)):
    payload = decode_jwt(token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid token: user_id not found") 
    
    return await update_push_token_user(user_id, push_token)

