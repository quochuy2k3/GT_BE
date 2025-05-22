from typing import List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status, Path, BackgroundTasks
from beanie import PydanticObjectId
from bson import ObjectId
from datetime import datetime

from config.jwt_bearer import JWTBearer
from config.jwt_handler import decode_jwt
from service.couple_service import (
    get_couples_by_user, 
    get_couple_by_id, 
    get_couple_by_users,
    create_couple,
    delete_couple_by_id,
    send_reminder
)
from schemas.couple import CoupleResponse, CoupleDetailResponse, CoupleReminderSchema
from models.couple import Couple
from models.user import User
from models.tracker import Tracker
from models.routine import Routine
from service.routine_service import get_routine_by_user_id

router = APIRouter(
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Not authenticated"},
        status.HTTP_403_FORBIDDEN: {"description": "Not authorized"},
        status.HTTP_404_NOT_FOUND: {"description": "Resource not found"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Internal server error"}
    }
)


@router.get(
    "/", 
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Get current user's couple",
    description="Get the couple relationship where the authenticated user is a member, including partner's today routine and full tracker information"
)
async def get_user_couple(token: str = Depends(JWTBearer())):
    """
    Get the couple relationship where the current user is a member.
    The response includes:
    - Couple basic information (id, created_at)
    - Partner information (id, fullname, email, avatar, streak)
    - Partner's today routine data
    - Partner's complete today tracker data including image URL, class summary, and timestamp
    
    Returns information about the couple relationship.
    """
    try:
        # Extract and validate user ID from token
        payload = decode_jwt(token)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token: user_id not found"
            )
            
        user_id = PydanticObjectId(user_id)
        
        # Get the couple for this user
        couple = await get_couples_by_user(user_id)
        if not couple:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No couple relationship found for this user"
            )
        return couple
    except HTTPException:
        # Re-throw HTTP exceptions as is
        raise
    except Exception as e:
        # Log the exception here if needed
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )

@router.delete(
    "/{couple_id}", 
    status_code=status.HTTP_200_OK,
    summary="Delete a couple by ID",
    description="Delete a couple relationship by its ID and related accepted friend request"
)
async def delete_couple(
    couple_id: str = Path(..., description="The ID of the couple to delete"),
    token: str = Depends(JWTBearer())
):
    """
    Delete a couple relationship by its ID and related accepted friend request.
    
    Args:
        couple_id: The ID of the couple to delete
        token: JWT token for authentication
        
    Returns:
        Success message if deleted successfully
    """
    try:
        # Extract and validate user ID from token
        payload = decode_jwt(token)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token: user_id not found"
            )
        
        # Validate couple_id format
        try:
            couple_id = PydanticObjectId(couple_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid couple_id format"
            )
        
        # Get the couple to check if the user is authorized
        couple = await Couple.get(couple_id)
        if not couple:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Couple not found"
            )
        
        # Check if the user is authorized to delete this couple
        user_id = PydanticObjectId(user_id)
        if couple.user_1 != user_id and couple.user_2 != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this couple"
            )
        
        # Delete the couple and related accepted request
        result = await delete_couple_by_id(couple_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Couple not found"
            )
        
        return {"message": "Couple and related accepted request deleted successfully"}
    except HTTPException:
        # Re-throw HTTP exceptions as is
        raise
    except Exception as e:
        # Log the exception here if needed
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )

@router.post(
    "/reminder",
    status_code=status.HTTP_200_OK,
    summary="Send reminder to partner",
    description="Send reminder to partner"
)
async def reminder(
    data: CoupleReminderSchema, 
    background_tasks: BackgroundTasks = BackgroundTasks(),
    token: str = Depends(JWTBearer())
):
    """
    Send reminder to partner
    """
    try:
        # Extract and validate user ID from token
        payload = decode_jwt(token)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token: user_id not found"
            )
        if not data.partner_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid partner_id"
            )
        
        user_id = PydanticObjectId(user_id)
        user_current = await User.get(user_id)
        if not user_current:    
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        user_partner = await User.get(data.partner_id)
        print(user_partner)
        if not user_partner:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        background_tasks.add_task(send_reminder, user_current, user_partner)
        # await send_reminder(user_current, user_partner)
        return {"message": "Reminder task scheduled successfully"}
    except HTTPException:
        # Re-throw HTTP exceptions as is
        raise
    except Exception as e:
        # Log the exception here if needed
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )