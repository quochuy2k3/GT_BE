import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from fastapi import HTTPException
import httpx
import logging
import asyncio
from config.config import Settings
from typing import Dict, Union, Optional

logger = logging.getLogger(__name__)

# Load email settings once during module initialization
SENDER_EMAIL = Settings().SENDER_EMAIL
SENDER_PASSWORD = Settings().SENDER_PASSWORD
SMTP_SERVER = Settings().SMTP_SERVER
SMTP_PORT = Settings().SMTP_PORT

async def send_email_request_friend(user_current, user_partner) -> Dict[str, Union[int, str]]:
    """
    Send a friend request email notification.
    
    Args:
        user_current: The user sending the request
        user_partner: The user receiving the request
        
    Returns:
        Dict with status and message
        
    Raises:
        HTTPException: If email sending fails
    """
    if not user_current or not user_partner:
        raise HTTPException(status_code=400, detail="Both users must be provided")
        
    if not hasattr(user_partner, 'email') or not user_partner.email:
        raise HTTPException(status_code=400, detail="Target user does not have an email address")
    
    subject = f"Lời mời kết bạn mới từ {user_current.fullname}"

    body = f"""
    <html>
        <body style="font-family: Arial, sans-serif; color: #333; background-color: #f4f7fa;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; background-color: #ffffff; border-radius: 8px; box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);">
                
                <!-- Header with Logo -->

                <!-- Main Title -->
                <h2 style="text-align: center; color: #333; font-size: 26px;">{user_current.fullname} đã gửi cho bạn một lời mời kết bạn</h2>
                
                <!-- Sub Text -->
                <p style="font-size: 16px; text-align: center; margin-top: 16px;">
                    Kết nối và bắt đầu chia sẻ những khoảnh khắc cùng nhau. Nhấn vào nút bên dưới để xem lời mời.
                </p>

                <!-- Button -->
                <div style="text-align: center; margin-top: 30px;">
                    <a href="https://www.facebook.com/VQH306" 
                    style="background-color: #4CAF50; color: white; padding: 14px 28px; border-radius: 30px; font-size: 18px; text-decoration: none; font-weight: bold; display: inline-block;">
                        Xem lời mời kết bạn
                    </a>
                </div>

                <!-- Footer -->
                <hr style="border: 1px solid #eee; margin: 40px 0;">
                <footer style="text-align: center; font-size: 12px; color: #aaa;">
                    <p>Cảm ơn bạn đã đồng hành cùng Glow Track!</p>
                    <a href="https://www.facebook.com/VQH306" style="color: #aaa; text-decoration: none;">Liên hệ hỗ trợ</a>
                </footer>
            </div>
        </body>
    </html>
    """

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            msg = MIMEMultipart()
            msg['From'] = "Glow Track - Go Together"
            msg['To'] = user_partner.email
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'html'))
            server.sendmail(SENDER_EMAIL, user_partner.email, msg.as_string())
        logger.info(f"Email sent successfully to {user_partner.email}")
        return {"status": 200, "message": "Friend request email sent successfully"}
    except Exception as e:
        logger.error(f"Error in send_email_request_friend: {str(e)}")
        return {"status": 500, "message": f"Error sending email: {str(e)}"}

async def push_notification(push_token: str, title: str, body: str, data: Optional[Dict] = None) -> bool:
    """
    Send a push notification to a device with the specified token.
    
    Args:
        push_token: The device push notification token
        title: The notification title
        body: The notification body text
        data: Optional additional data for the notification
        
    Returns:
        bool: True if notification was sent successfully, False otherwise
    """
    if not push_token:
        logger.warning("Cannot send push notification: No push token provided")
        return False
        
    message = {
        "to": push_token,
        "sound": "default",
        "title": title,
        "body": body,
        "badge": 1,
    }
    
    # Add additional data if provided
    if data:
        message["data"] = data
        
    url = "https://exp.host/--/api/v2/push/send"
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=message)
            if response.status_code == 200:
                logger.info(f"Notification sent successfully to {push_token}")
                return True
            else:
                logger.error(f"Failed to send notification to {push_token}: {response.text}")
                return False
    except Exception as e:
        logger.error(f"Error sending push notification: {str(e)}")
        return False

async def send_request_friend_notification(user_current, user_partner) -> Dict[str, Union[int, str]]:
    """
    Send a friend request notification to a user.
    
    Args:
        user_current: The user sending the request
        user_partner: The user receiving the request
        
    Returns:
        Dict with status and message
    """
    if not user_partner:
        logger.warning("Cannot send notification: No target user provided")
        return {"status": 400, "message": "No target user provided"}
        
    # Skip if user doesn't have a push token but don't fail
    if not hasattr(user_partner, 'push_token') or not user_partner.push_token:
        logger.info(f"User {user_partner.id} has no push token, skipping notification")
        return {"status": 200, "message": "User has no push token, notification skipped"}
    
    try:
        title = f"Bạn có lời mời kết bạn mới"
        body = f"{user_current.fullname} muốn kết bạn với bạn."
        
        # Create data payload with user info
        data = {
            "type": "friend_request",
            "sender_id": str(user_current.id)
        }
        
        # Attempt to add avatar URL if available
        if hasattr(user_current, 'avatar') and user_current.avatar:
            data["sender_avatar"] = user_current.avatar
            
        result = await push_notification(user_partner.push_token, title, body, data)
        
        if result:
            return {"status": 200, "message": "Notification sent successfully"}
        else:
            return {"status": 500, "message": "Failed to send notification"}
    except Exception as e:
        logger.error(f"Error in send_request_friend_notification: {str(e)}")
        return {"status": 500, "message": f"Error sending notification: {str(e)}"}

async def send_reminder_notification(user_current, user_partner):
    """
    Send a reminder notification to a user.
    
    Args:
        user_current: The user sending the reminder
        user_partner: The user receiving the reminder
        
    Returns:
        Dict with status and message
    """
    if not user_partner:
        logger.warning("Cannot send notification: No target user provided")
        return {"status": 400, "message": "No target user provided"}
        
    # Skip if user doesn't have a push token but don't fail
    print(user_partner.push_token)
    print(user_partner.push_token)
    print(user_partner.push_token)
    print(user_partner.push_token)
    print(user_partner.push_token)
    print(user_partner.push_token)
    print(user_partner.push_token)
    if not hasattr(user_partner, 'push_token') or not user_partner.push_token:
        logger.info(f"User {user_partner.id} has no push token, skipping notification")
        return {"status": 200, "message": "User has no push token, notification skipped"}
    
    try:
        title = f"Reminder"
        body = f"{user_current.fullname} đã nhắc bạn thực hiện thói quen trong ngày ."

        result = await push_notification(user_partner.push_token, title, body)
        
        if result:
            return {"status": 200, "message": "Notification sent successfully"}
        else:
            return {"status": 500, "message": "Failed to send notification"}
    except Exception as e:
        logger.error(f"Error in send_reminder_notification: {str(e)}")
        return {"status": 500, "message": f"Error sending notification: {str(e)}"}
    

async def send_reminder_email(user_current, user_partner):
    """
    Send a reminder email to a user.
    """
   
    if not user_current or not user_partner:
        logger.error("Both users must be provided")
        return {"status": 400, "message": "Both users must be provided"}
        
    if not hasattr(user_partner, 'email') or not user_partner.email:
        logger.error("Target user does not have an email address")
        return {"status": 400, "message": "Target user does not have an email address"}
    
    subject = f"Nhắc nhở từ {user_current.fullname}"

    body = f"""
    <html>
        <body style="font-family: Arial, sans-serif; color: #333; background-color: #f4f7fa;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; background-color: #ffffff; border-radius: 8px; box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);">
                
                <!-- Header with Logo -->

                <!-- Main Title -->
                <h2 style="text-align: center; color: #333; font-size: 26px;">{user_current.fullname} đã nhắc bạn thực hiện thói quen trong ngày</h2>
                
                <!-- Sub Text -->
                <p style="font-size: 16px; text-align: center; margin-top: 16px;">
                    Đừng quên hoàn thành thói quen của bạn hôm nay. Nhấn vào nút bên dưới để xem chi tiết.
                </p>

                <!-- Button -->
                <div style="text-align: center; margin-top: 30px;">
                    <a href="https://www.facebook.com/VQH306" 
                    style="background-color: #4CAF50; color: white; padding: 14px 28px; border-radius: 30px; font-size: 18px; text-decoration: none; font-weight: bold; display: inline-block;">
                        Xem chi tiết nhắc nhở
                    </a>
                </div>

                <!-- Footer -->
                <hr style="border: 1px solid #eee; margin: 40px 0;">
                <footer style="text-align: center; font-size: 12px; color: #aaa;">
                    <p>Cảm ơn bạn đã đồng hành cùng Glow Track!</p>
                    <a href="https://www.facebook.com/VQH306" style="color: #aaa; text-decoration: none;">Liên hệ hỗ trợ</a>
                </footer>
            </div>
        </body>
    </html>
    """

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            msg = MIMEMultipart()
            msg['From'] = "Glow Track - Go Together"
            msg['To'] = user_partner.email
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'html'))
            server.sendmail(SENDER_EMAIL, str(user_partner.email), msg.as_string())
        logger.info(f"Email sent successfully to {user_partner.email}")
        return {"status": 200, "message": "Reminder email sent successfully"}
    except Exception as e:
        logger.error(f"Error in send_reminder_email: {str(e)}")
        return {"status": 500, "message": f"Error sending email: {str(e)}"}
