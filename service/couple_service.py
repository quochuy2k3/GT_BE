from beanie import PydanticObjectId
from typing import List, Optional, Dict, Any, Union
from service.send_notification_service import send_reminder_email, send_reminder_notification
from datetime import datetime
import logging

from models.couple import Couple
from models.user import User
from models.routine import Routine
from models.tracker import Tracker
from models.request import Request, StatusEnum
from routes.routine import serialize_day
from schemas.routine import DaySchema, DayResponseSchema

# Khởi tạo logger
logger = logging.getLogger(__name__)

async def create_couple(user_1_id: PydanticObjectId, user_2_id: PydanticObjectId) -> Couple:
    """
    Create a new couple between two users
    
    Args:
        user_1_id: ID of the first user
        user_2_id: ID of the second user
        
    Returns:
        The created couple document
    """
    # Check if a couple already exists between these users
    existing_couple = await get_couple_by_users(user_1_id, user_2_id)
    if existing_couple:
        return existing_couple
    
    # Create a new couple
    couple = Couple(
        user_1=user_1_id,
        user_2=user_2_id
    )
    await couple.create()
    return couple


async def get_couple_by_users(user_1_id: PydanticObjectId, user_2_id: PydanticObjectId) -> Optional[Couple]:
    """
    Get a couple by its user IDs
    
    Args:
        user_1_id: ID of the first user
        user_2_id: ID of the second user
        
    Returns:
        The couple document or None if not found
    """
    # Check both user order possibilities
    couple = await Couple.find_one(
        {"$or": [
            {"user_1": user_1_id, "user_2": user_2_id},
            {"user_1": user_2_id, "user_2": user_1_id}
        ]}
    )
    return couple


async def _get_partner_tracker(partner_id: PydanticObjectId) -> Optional[Tracker]:
    """
    Get today's tracker for a user
    
    Args:
        partner_id: ID of the user
        
    Returns:
        Today's tracker or None if not found
    """
    today = datetime.now().date()
    return await Tracker.find_one(
        {"user_id": partner_id, "date": today},
        sort=[("timeTracking", -1)]  # Get the latest tracker for today
    )


async def _get_partner_today_routine(partner_id: PydanticObjectId) -> Optional[DaySchema]:
    """
    Get today's routine for a user
    
    Args:
        partner_id: ID of the user
        
    Returns:
        Today's routine as DaySchema or None if not found
    """
    today_name = datetime.now().strftime("%A")
    partner_routine = await Routine.find_one(Routine.user_id == partner_id)
    
    if not partner_routine:
        return None
        
    for day in partner_routine.days:
        if day.day_of_week.lower() == today_name.lower():
            today_data = serialize_day(day)
            return DayResponseSchema(
                routine_name=partner_routine.routine_name,
                push_token=partner_routine.push_token,
                today=DaySchema.model_validate(today_data)
            )
    
    return None


def _format_tracker_response(tracker: Tracker) -> Dict[str, Any]:
    """
    Format tracker data for API response
    
    Args:
        tracker: Tracker object
        
    Returns:
        Formatted tracker data ready for API response
    """
    return {
        "id": str(tracker.id),
        "user_id": str(tracker.user_id),
        "img_url": tracker.img_url,
        "date": tracker.date.isoformat(),
        "class_summary": tracker.class_summary,
        "timeTracking": tracker.timeTracking
    }


async def _format_partner_data(partner: User, tracker: Optional[Tracker], today_routine: Optional[DaySchema]) -> Dict[str, Any]:
    """
    Format partner data for API response
    
    Args:
        partner: Partner user object
        tracker: Today's tracker (optional)
        today_routine: Today's routine (optional)
        
    Returns:
        Formatted partner data ready for API response
    """
    data = {
        "id": str(partner.id),
        "fullname": partner.fullname,
        "email": partner.email,
        "avatar": partner.avatar,
        "streak": partner.streak,
        "today_tracker": None,
        "today_routine": today_routine
    }
    
    if tracker:
        data["today_tracker"] = _format_tracker_response(tracker)
    
    return data


async def get_couple_by_id(couple_id: PydanticObjectId) -> Optional[Dict[str, Any]]:
    """
    Get a couple by its ID with detailed response format
    
    Args:
        couple_id: The ID of the couple to retrieve
        
    Returns:
        Detailed couple information or None if not found
    """
    couple = await Couple.get(couple_id)
    if not couple:
        return None
    
    # Determine who is the partner (using user_2 as partner for this endpoint)
    partner = await User.get(couple.user_2)
    if not partner:
        return None
    
    # Get partner's data
    partner_tracker = await _get_partner_tracker(partner.id)
    partner_today_routine = await _get_partner_today_routine(partner.id)
    
    # Create response object
    result = {
        "id": str(couple.id),
        "created_at": couple.created_at,
        "partner": await _format_partner_data(partner, partner_tracker, partner_today_routine)
    }
    
    return result


async def get_couples_by_user(user_id: PydanticObjectId) -> Dict[str, Any]:
    """
    Get the user's couple relationship with detailed response format
    
    Args:
        user_id: The ID of the user
        
    Returns:
        Detailed information about the couple relationship
    """
    couple = await Couple.find_one(
        {"$or": [
            {"user_1": user_id},
            {"user_2": user_id}
        ]}
    )
    
    if not couple:
        return {}
    
    # Determine who is the partner
    partner_id = couple.user_2 if couple.user_1 == user_id else couple.user_1
    
    # Get partner data
    partner = await User.get(partner_id)
    if not partner:
        return {}
    
    # Get partner's data
    partner_tracker = await _get_partner_tracker(partner.id)
    partner_today_routine = await _get_partner_today_routine(partner.id)
    
    # Create response object
    couple_data = {
        "id": str(couple.id),
        "created_at": couple.created_at,
        "partner": await _format_partner_data(partner, partner_tracker, partner_today_routine)
    }
    
    return couple_data


async def delete_couple_by_id(couple_id: PydanticObjectId) -> bool:
    """
    Delete a couple by its ID and related accepted request
    
    Args:
        couple_id: The ID of the couple to delete
        
    Returns:
        True if deleted successfully, False if not found
    """
    couple = await Couple.get(couple_id)
    if not couple:
        logger.warning(f"Attempt to delete non-existent couple with ID: {couple_id}")
        return False
    
    # Delete any accepted requests between these users
    delete_result = await Request.find({
        "$or": [
            {"user_id": couple.user_1, "partner_id": couple.user_2},
            {"user_id": couple.user_2, "partner_id": couple.user_1}
        ],
        "status": StatusEnum.accepted
    }).delete()
    
    logger.info(f"Deleted {delete_result} accepted requests between users {couple.user_1} and {couple.user_2}")
    
    # Delete the couple
    await couple.delete()
    logger.info(f"Deleted couple with ID: {couple_id} between users {couple.user_1} and {couple.user_2}")
    
    return True

async def send_reminder(user_current, user_partner) :
   await send_reminder_email(user_current, user_partner)
   await send_reminder_notification(user_current, user_partner)
   return {"status": 200, "message": "Reminder sent successfully"}
    
