from datetime import datetime, timedelta
from config.config import Settings
from fastapi import APIRouter, Body, HTTPException, Depends
from pydantic import BaseModel, EmailStr
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from passlib.context import CryptContext
from monitoring.fastapi_metrics import increment_user_registration, increment_user_login

from config.jwt_handler import sign_jwt, decode_jwt
from database.database import add_user
from models.user import User
from schemas.user import UserSignIn, UserSignUp
from service.routine_service import create_routine_for_new_user

router = APIRouter()
hash_helper = CryptContext(schemes=["bcrypt"], deprecated="auto")
otp_storage = {}
print(otp_storage)
class EmailRequest(BaseModel):
    email: EmailStr

class OTPVerifyRequest(BaseModel):
    email: str
    otp: str

SENDER_EMAIL = Settings().SENDER_EMAIL
SENDER_PASSWORD = Settings().SENDER_PASSWORD
SMTP_SERVER = Settings().SMTP_SERVER
SMTP_PORT = Settings().SMTP_PORT


@router.post("/send-otp", response_description="Sign In")
async def send_otp(request: EmailRequest):
    user = await User.find_one(User.email == request.email )
    if user:
        raise HTTPException(status_code=409, detail="User with provided email or phone already exists")
    otp = str(random.randint(10000, 99999))
    otp_expiry = datetime.utcnow() + timedelta(minutes=5)

    otp_storage[request.email] = {"otp": otp, "expiry": otp_expiry}

    subject = "Your One-Time Password (OTP)"
    body = f"""
    <html>
        <body style="font-family: Arial, sans-serif; color: #333; background-color: #f4f7fa;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; background-color: #ffffff; border-radius: 8px; box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);">
                <!-- Header with Logo -->
                <div style="text-align: center; margin-bottom: 16px; border-radius: 24px;">
                    <img src="https://res.cloudinary.com/dxplnavr4/image/upload/v1743755731/kmfhg0usqjdh3bjyev9p.png" alt="Glow Track Logo" style="max-width: 160px; border-radius: 24px;">
                </div>
                <h2 style="text-align: center; color: #4CAF50; font-size: 28px; font-weight: bold;">Your OTP Code</h2>
                <p style="font-size: 16px; text-align: center;">We received a request to send you a One-Time Password (OTP) to verify your identity. Your OTP is:</p>
              
       <div style="text-align: center; margin-top: 10px;">
         <h3 style="text-align: center; font-size: 36px; color: #4CAF50; font-weight: bold;">{otp}</h3>
                <p style="font-size: 16px; text-align: center;">It will expire in 5 minutes. Please use it before the expiration time.</p>
    <a href="https://www.facebook.com/VQH306" 
       style="text-decoration: none; background-color: #4CAF50; color: white; 
              padding: 14px 24px; border-radius: 30px; font-size: 18px; font-weight: bold; 
              display: inline-block; transition: background-color 0.3s; 
              width: auto; margin: 10px 0;">
        Go to Mobile App
    </a>
</div>

                <hr style="border: 1px solid #ddd; margin: 30px 0;">
                <p style="font-size: 14px; color: #777; text-align: center;">If you did not request this OTP, please ignore this email.</p>

                <!-- Footer with Social Media Links -->
                <footer style="text-align: center; font-size: 12px; color: #888; margin-top: 40px;">
                    <p>Thank you for using our service!</p>
                        <a href="https://www.facebook.com/VQH306" style="text-decoration: none; color: #888; margin: 0 10px;">
                            CONTACT US
                        </a>
                </footer>
            </div>
        </body>
    </html>
    """

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()

        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        # Tạo nội dung email với HTML
        msg = MIMEMultipart()
        msg['From'] = "Glow Track - Go Together"
        msg['To'] = request.email
        msg['Subject'] = subject

        msg.attach(MIMEText(body, 'html'))

        server.sendmail(SENDER_EMAIL, str(request.email), msg.as_string())
        server.quit()

        return {"status": 200,"message": "OTP sent successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error sending OTP email: {e}")


@router.post("/verify-otp", response_description="Verify OTP")
async def verify_otp(request: OTPVerifyRequest):

    stored_data = otp_storage.get(request.email)

    if not stored_data:
        raise HTTPException(status_code=400, detail="OTP not found or expired")

    if stored_data["otp"] == request.otp:
        if stored_data["expiry"] > datetime.utcnow():
            del otp_storage[request.email]
            return {"status": 200, "message": "OTP verified successfully"}
        else:
            del otp_storage[request.email]
            raise HTTPException(status_code=400, detail="OTP expired")

    raise HTTPException(status_code=400, detail="Invalid OTP")

@router.post("/sign-in", response_description="Sign In")
async def sign_in(user_credentials: UserSignIn = Body(...)):
    print(user_credentials)
    user_exists = await User.find_one(User.email == user_credentials.email)
    print(user_exists)
    if user_exists:
        password_valid = hash_helper.verify(user_credentials.password, user_exists.password)
        if password_valid:
            increment_user_login()  # Increment login counter
            return sign_jwt(str(user_exists.id), user_exists.role, str(user_exists.email), user_exists.phone)

        raise HTTPException(status_code=403, detail="Incorrect password")

    raise HTTPException(status_code=403, detail="Incorrect email ")


@router.post("/sign-up", response_description="Sign In")
async def user_signup(user: UserSignUp = Body(...)):
    admin_exists = await User.find_one(User.email == user.email and User.phone == user.phone)
    if admin_exists:
        raise HTTPException(status_code=409, detail="User with provided email or phone already exists")

    try:
        user.password = hash_helper.hash(user.password)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error hashing password: {str(e)}")
    dataUser = User(
        fullname=user.fullname,
        email=user.email,
        password=user.password,
        phone=user.phone,
        gender=user.gender,
        avatar=user.avatar,
        role="baseUser",
        streak=0
    )
    new_user = await add_user(dataUser)
    try:
        await create_routine_for_new_user(new_user.id)
        increment_user_registration()  # Increment registration counter
        return sign_jwt(str(new_user.id), new_user.role, str(new_user.email), new_user.phone)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/resend-otp", response_description="Resend OTP")
async def resend_otp(request: EmailRequest):
    stored_data = otp_storage.get(request.email)

    # Nếu OTP đã được gửi và chưa hết hạn, thay đổi OTP cũ
    if stored_data and stored_data["expiry"] > datetime.utcnow():
        # Cập nhật lại OTP và thời gian hết hạn
        otp = str(random.randint(10000, 99999))
        otp_expiry = datetime.utcnow() + timedelta(minutes=5)

        otp_storage[request.email] = {"otp": otp, "expiry": otp_expiry}
    else:
        # Nếu OTP đã hết hạn hoặc chưa được gửi, tạo OTP mới
        otp = str(random.randint(10000, 99999))
        otp_expiry = datetime.utcnow() + timedelta(minutes=5)

        otp_storage[request.email] = {"otp": otp, "expiry": otp_expiry}

    # Gọi lại hàm send_otp để gửi email
    return await send_otp(request)
