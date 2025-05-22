from datetime import datetime
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, Body, HTTPException, Depends, BackgroundTasks, status, Path, Query
from service.request import (
    check_can_create_request, 
    create_send_request, 
    get_sent_request, 
    get_list_request_received, 
    send_request_friend,
    accept_request,
    cancel_request,
    reject_request,
    delete_sent_request,
    cleanup_other_requests
)
from pydantic import BaseModel

from config.jwt_bearer import JWTBearer
from config.jwt_handler import decode_jwt
from models.user import User
from models.request import Request, StatusEnum
from schemas.request import (
    CreateRequestSchema, 
    RequestResponseSchema, 
    ReceivedRequestSchema,
    SentRequestSchema
)
from beanie import PydanticObjectId

router = APIRouter(
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Bad Request"},
        status.HTTP_401_UNAUTHORIZED: {"description": "Not authenticated"},
        status.HTTP_403_FORBIDDEN: {"description": "Not authorized"},
        status.HTTP_404_NOT_FOUND: {"description": "Resource not found"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Internal server error"}
    }
)

@router.post(
    "/create-request", 
    response_model=RequestResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Send a friend request",
    description="Send a friend request to another user by email address"
)
async def create_friend_request(
    request_data: CreateRequestSchema = Body(...), 
    background_tasks: BackgroundTasks = BackgroundTasks(), 
    token: str = Depends(JWTBearer())
):
    """
    Send a friend request to another user.
    
    - **email**: Email address of the user to send the request to
    
    Returns the created friend request or an error.
    """
    try:
        payload = decode_jwt(token) 
        user_id = payload.get("sub")
        user_id = PydanticObjectId(user_id)
        
        # Verify target user exists
        user_exists = await User.find_one(User.email == request_data.email)
        if not user_exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="User not found"
            )
        
        # Check if trying to send request to self
        if str(user_exists.id) == str(user_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Cannot send friend request to yourself"
            )
        
        # Check if request already exists
        can_create_request = await check_can_create_request(user_id, user_exists.id)
        if not can_create_request:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, 
                detail="Friend request already exists between these users"
            )
        
        # Create and save the request
        request = await create_send_request(user_id, user_exists.id)
        
        # Send notifications in background
        background_tasks.add_task(send_request_friend, request, user_exists)
        
        return {
            "id": request.id,
            "user_id": request.user_id,
            "partner_id": request.partner_id,
            "status": request.status,
            "created_at": request.created_at,
            "message": "Friend request sent successfully"
        }
    except HTTPException:
        # Re-raise HTTP exceptions to preserve status code
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )

@router.post(
    "/{request_id}/accept", 
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Accept a friend request",
    description="Accept a pending friend request by ID and delete any other pending requests between the two users"
)
async def accept_friend_request(
    request_id: str = Path(..., description="The ID of the friend request to accept"), 
    background_tasks: BackgroundTasks = BackgroundTasks(),
    token: str = Depends(JWTBearer())
):
    """
    Accept a pending friend request.
    
    - **request_id**: The ID of the request to accept
    
    Returns the updated friend request with status 'accepted' or an error.
    Note: When a request is accepted, any other pending requests between the two users will be automatically deleted.
    """
    try:
        payload = decode_jwt(token) 
        user_id = payload.get("sub")
        user_id = PydanticObjectId(user_id)
        request_id = PydanticObjectId(request_id)
        
        # Chấp nhận lời mời kết bạn
        request = await accept_request(request_id, user_id)
        
        # Xóa các lời mời kết bạn dư thừa trong background
        background_tasks.add_task(
            cleanup_other_requests, 
            user_id=request.user_id,
            partner_id=request.partner_id,
            accepted_request_id=request.id
        )
        
        # Trả về thông tin chi tiết về request đã được chấp nhận
        return {
            "id": str(request.id),
            "user_id": str(request.user_id),
            "partner_id": str(request.partner_id),
            "status": request.status,
            "created_at": request.created_at,
            "message": "Friend request accepted successfully",
            "note": "Cleanup of redundant friend requests is being processed in the background"
        }
    except HTTPException:
        # Re-raise HTTP exceptions to preserve status code
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )

@router.delete(
    "/{request_id}/sent", 
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Delete a sent friend request",
    description="Delete a pending friend request that you sent to another user"
)
async def delete_sent_friend_request(
    request_id: str = Path(..., description="The ID of the friend request to delete"),
    token: str = Depends(JWTBearer())
):
    """
    Delete a friend request that you sent to another user.
    
    - **request_id**: The ID of the sent request to delete
    
    Returns a confirmation message or an error.
    """
    try:
        payload = decode_jwt(token) 
        user_id = payload.get("sub")
        user_id = PydanticObjectId(user_id)
        request_id = PydanticObjectId(request_id)
        result = await delete_sent_request(request_id, user_id)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )

@router.delete(
    "/{request_id}/received", 
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Reject a received friend request",
    description="Reject a pending friend request received from another user"
)
async def reject_friend_request(
    request_id: str = Path(..., description="The ID of the friend request to reject"),
    token: str = Depends(JWTBearer())
):
    """
    Reject a friend request that you received from another user.
    
    - **request_id**: The ID of the received request to reject
    
    Returns a confirmation message or an error.
    """
    try:
        payload = decode_jwt(token) 
        user_id = payload.get("sub")
        user_id = PydanticObjectId(user_id)
        request_id = PydanticObjectId(request_id)
        
        result = await reject_request(request_id, user_id)
        return result
    except HTTPException:
        # Re-raise HTTP exceptions to preserve status code
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )

@router.delete(
    "/{request_id}", 
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Delete any friend request",
    description="Delete any pending friend request (sent or received). For more specific actions, use the dedicated endpoints."
)
async def delete_any_friend_request(
    request_id: str = Path(..., description="The ID of the friend request to delete"),
    token: str = Depends(JWTBearer())
):
    """
    Automatically detect if you are the sender or receiver of the request and perform the appropriate action.
    This is a convenience endpoint - you can use the more specific endpoints for clarity.
    
    - **request_id**: The ID of the request to delete
    
    Returns a confirmation message or an error.
    """
    try:
        payload = decode_jwt(token) 
        user_id = payload.get("sub")
        user_id = PydanticObjectId(user_id)
        request_id = PydanticObjectId(request_id)
        
        # Check if the request exists
        request = await Request.find_one(Request.id == request_id)
        if not request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Friend request not found"
            )
        
        # Determine action based on user's role
        if request.user_id == user_id:
            # User is canceling their own sent request
            result = await delete_sent_request(request_id, user_id)
            return result
        elif request.partner_id == user_id:
            # User is rejecting a received request
            result = await reject_request(request_id, user_id)
            return result
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this request"
            )
    except HTTPException:
        # Re-raise HTTP exceptions to preserve status code
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )

@router.get(
    "/received", 
    response_model=List[ReceivedRequestSchema],
    status_code=status.HTTP_200_OK,
    summary="List received friend requests",
    description="Get a list of pending friend requests received by the authenticated user with sender information"
)
async def list_received_requests(
    token: str = Depends(JWTBearer())
):
    """
    Get a list of pending friend requests received by the current user.
    Includes sender information (fullname, email, avatar).
    
    Returns a list of friend request objects or an error.
    """
    try:
        payload = decode_jwt(token) 
        user_id = payload.get("sub")
        user_id = PydanticObjectId(user_id)
        
        return await get_list_request_received(user_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch received requests: {str(e)}"
        )

@router.get(
    "/sent", 
    response_model=List[SentRequestSchema],
    status_code=status.HTTP_200_OK,
    summary="List sent friend requests",
    description="Get a list of pending friend requests sent by the authenticated user with receiver information"
)
async def list_sent_requests(
    token: str = Depends(JWTBearer())
):
    """
    Get a list of pending friend requests sent by the current user.
    Includes receiver information (fullname, email, avatar).
    
    Returns a list of friend request objects or an error.
    """
    try:
        payload = decode_jwt(token) 
        user_id = payload.get("sub")
        user_id = PydanticObjectId(user_id)
        
        return await get_sent_request(user_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch sent requests: {str(e)}"
        )
