from models.request import Request, StatusEnum
from models.user import User
from datetime import datetime
from typing import Dict, List, Optional, Union, Any
from fastapi import HTTPException
from beanie import PydanticObjectId
from service.send_notification_service import send_request_friend_notification, send_email_request_friend
import logging

# Khởi tạo logger
logger = logging.getLogger(__name__)

async def check_can_create_request(user_id: PydanticObjectId, partner_id: PydanticObjectId) -> bool:
    """
    Check if a request can be created between two users.
    
    Args:
        user_id: The ID of the user creating the request
        partner_id: The ID of the partner receiving the request
    
    Returns:
        bool: True if a request can be created, False otherwise
    """
    existing_request = await Request.find_one({
        "$or": [
            {"user_id": user_id, "partner_id": partner_id},
            {"user_id": partner_id, "partner_id": user_id}
        ],
        "status": {"$in": [StatusEnum.pending, StatusEnum.accepted]}
    })
    return existing_request is None

async def create_send_request(user_id: PydanticObjectId, partner_id: PydanticObjectId) -> Request:
    """
    Create a new friend request.
    
    Args:
        user_id: The ID of the user creating the request
        partner_id: The ID of the partner receiving the request
    
    Returns:
        Request: The created request object
    
    Raises:
        HTTPException: If there's an error creating the request
    """
    try:
        request = Request(user_id=user_id, partner_id=partner_id)
        return await request.save()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create request: {str(e)}")

async def send_request_friend(request: Request, user_exists: User) -> Dict[str, Union[int, str]]:
    """
    Send a friend request notification and email.
    
    Args:
        request: The request object
        user_exists: The user receiving the request
    
    Returns:
        Dict: Response with status and message
    
    Raises:
        HTTPException: If the current user can't be found or notification fails
    """
    try:
        current_user = await User.find_one(User.id == request.user_id)
        if not current_user:
            raise HTTPException(status_code=404, detail="Current user not found")
            
        # Try to send notification first, if it fails, still try to send email
        try:
            if user_exists.push_token:
                await send_request_friend_notification(current_user, user_exists)
        except Exception as e:
            # Log the error but continue with email
            print(f"Notification error: {str(e)}")
            
        # Send email notification
        await send_email_request_friend(current_user, user_exists)
        return {"status": 200, "message": "Request friend sent successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send request: {str(e)}")

async def get_list_request_received(user_id: PydanticObjectId) -> List[Dict[str, Any]]:
    """
    Get a list of pending friend requests received by a user.
    Includes information about the sender (user_id).
    
    Args:
        user_id: The ID of the user
    
    Returns:
        List[Dict]: List of pending requests with sender information
    """
    try:
        # Lấy tất cả lời mời nhận được
        requests = await Request.find(Request.partner_id == user_id, Request.status == StatusEnum.pending).to_list()
        
        # Tạo danh sách ID của người gửi để query một lần
        sender_ids = [request.user_id for request in requests]
        
        # Lấy thông tin tất cả người gửi trong một lần query
        senders = await User.find({"_id": {"$in": sender_ids}}).to_list()
        
        # Tạo map để dễ dàng truy cập
        sender_map = {str(sender.id): sender for sender in senders}
        
        # Tạo kết quả
        result = []
        for request in requests:
            request_dict = request.dict()
            sender_id = str(request.user_id)
            
            # Thêm thông tin người gửi nếu có
            if sender_id in sender_map:
                sender = sender_map[sender_id]
                request_dict["sender_info"] = {
                    "fullname": sender.fullname,
                    "email": sender.email,
                    "avatar": sender.avatar
                }
            
            result.append(request_dict)
            
        return result
    except Exception as e:
        logger.error(f"Error fetching received requests: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch received requests: {str(e)}")

async def get_sent_request(user_id: PydanticObjectId) -> List[Dict[str, Any]]:
    """
    Get a list of pending friend requests sent by a user.
    Includes information about the receiver (partner_id).
    
    Args:
        user_id: The ID of the user
    
    Returns:
        List[Dict]: List of pending requests with receiver information
    """
    try:
        # Lấy tất cả lời mời đã gửi
        requests = await Request.find(Request.user_id == user_id, Request.status == StatusEnum.pending).to_list()
        
        # Tạo danh sách ID của người nhận để query một lần
        receiver_ids = [request.partner_id for request in requests]
        
        # Lấy thông tin tất cả người nhận trong một lần query
        receivers = await User.find({"_id": {"$in": receiver_ids}}).to_list()
        
        # Tạo map để dễ dàng truy cập
        receiver_map = {str(receiver.id): receiver for receiver in receivers}
        
        # Tạo kết quả
        result = []
        for request in requests:
            request_dict = request.dict()
            receiver_id = str(request.partner_id)
            
            # Thêm thông tin người nhận nếu có
            if receiver_id in receiver_map:
                receiver = receiver_map[receiver_id]
                request_dict["receiver_info"] = {
                    "fullname": receiver.fullname,
                    "email": receiver.email,
                    "avatar": receiver.avatar
                }
            
            result.append(request_dict)
            
        return result
    except Exception as e:
        logger.error(f"Error fetching sent requests: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch sent requests: {str(e)}")

async def accept_request(request_id: PydanticObjectId, user_id: PydanticObjectId) -> Request:
    """
    Accept a friend request and create a couple relationship.
    
    Args:
        request_id: The ID of the request to accept
        user_id: The ID of the user accepting the request
        
    Returns:
        Request: The updated request object
        
    Raises:
        HTTPException: If the request doesn't exist or user isn't authorized
    """
    request = await Request.find_one(Request.id == request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    if request.partner_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to accept this request")
        
    if request.status != StatusEnum.pending:
        raise HTTPException(status_code=400, detail=f"Request is already {request.status}")
    
    # Chuyển trạng thái của request hiện tại thành accepted
    request.status = StatusEnum.accepted
    await request.save()
    
    # Create a couple relationship between the users
    try:
        # Import here to avoid circular imports
        from service.couple_service import create_couple
        await create_couple(request.user_id, request.partner_id)
    except Exception as e:
        # Log the error but don't fail the request acceptance
        logger.error(f"Failed to create couple: {str(e)}")
    
    # Trả về request để API có thể phản hồi nhanh
    return request

async def cleanup_other_requests(user_id: PydanticObjectId, partner_id: PydanticObjectId, accepted_request_id: PydanticObjectId) -> int:
    """
    Xóa các lời mời kết bạn khác giữa hai người dùng sau khi một lời mời đã được chấp nhận.
    
    Args:
        user_id: ID của người dùng thứ nhất
        partner_id: ID của người dùng thứ hai
        accepted_request_id: ID của lời mời đã được chấp nhận (để loại trừ khỏi việc xóa)
        
    Returns:
        int: Số lượng lời mời đã bị xóa
    """
    # Tìm các lời mời kết bạn khác giữa hai người dùng
    other_requests = await Request.find({
        "$and": [
            {
                "$or": [
                    {"user_id": user_id, "partner_id": partner_id},
                    {"user_id": partner_id, "partner_id": user_id}
                ]
            },
            {"_id": {"$ne": accepted_request_id}},
            {"status": StatusEnum.pending}
        ]
    }).to_list()
    
    # Đếm số lượng lời mời cần xóa
    count = len(other_requests)
    
    # Xóa các lời mời này
    for other_request in other_requests:
        await other_request.delete()
    
    # Log kết quả
    logger.info(f"Deleted {count} redundant friend requests between users {user_id} and {partner_id}")
    
    return count

async def cancel_request(request_id: PydanticObjectId, user_id: PydanticObjectId) -> Dict[str, Union[int, str]]:
    """
    Cancel a friend request.
    
    Args:
        request_id: The ID of the request to cancel
        user_id: The ID of the user cancelling the request
        
    Returns:
        Dict: Response with status and message
        
    Raises:
        HTTPException: If the request doesn't exist or user isn't authorized
    """
    request = await Request.find_one(Request.id == request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    if request.user_id != user_id and request.partner_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to cancel this request")
        
    if request.status != StatusEnum.pending:
        raise HTTPException(status_code=400, detail=f"Cannot cancel request with status {request.status}")
    
    # Delete the request instead of changing status
    await request.delete()
    return {"status": 200, "message": "Friend request cancelled successfully"}

async def reject_request(request_id: PydanticObjectId, user_id: PydanticObjectId) -> Dict[str, Union[int, str]]:
    """
    Reject a friend request received by a user.
    
    Args:
        request_id: The ID of the request to reject
        user_id: The ID of the user rejecting the request
        
    Returns:
        Dict: Response with status and message
        
    Raises:
        HTTPException: If the request doesn't exist or user isn't authorized
    """
    request = await Request.find_one(Request.id == request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    if request.partner_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to reject this request")
        
    if request.status != StatusEnum.pending:
        raise HTTPException(status_code=400, detail=f"Cannot reject request with status {request.status}")
    
    # Delete the request instead of changing status
    await request.delete()
    return {"status": 200, "message": "Friend request rejected successfully"}

async def delete_sent_request(request_id: PydanticObjectId, user_id: PydanticObjectId) -> Dict[str, Union[int, str]]:
    """
    Delete a friend request sent by a user.
    
    Args:
        request_id: The ID of the request to delete
        user_id: The ID of the user who sent the request
        
    Returns:
        Dict: Response with status and message
        
    Raises:
        HTTPException: If the request doesn't exist or user isn't authorized
    """
    request = await Request.find_one(Request.id == request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    if request.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this request")
        
    if request.status != StatusEnum.pending:
        raise HTTPException(status_code=400, detail=f"Cannot delete request with status {request.status}")
    
    # Delete the request
    await request.delete()
    return {"status": 200, "message": "Friend request deleted successfully"}