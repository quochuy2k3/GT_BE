import jwt
import time
from datetime import datetime, timedelta
from typing import Dict
from fastapi import HTTPException
from config.config import Settings

# Khai báo bí mật và thuật toán
secret_key = Settings().secret_key  # Đảm bảo bảo mật
ALGORITHM = Settings().algorithm  # Đảm bảo thuật toán
ACCESS_TOKEN_EXPIRE_MINUTES = 1000  # Thời gian hết hạn token (ví dụ: 1000 phút)

# Hàm trả về token response
def token_response(token: str):
    return {"access_token": token, "token_type": "bearer"}

def sign_jwt(user_id: str, role: str, email: str, phone: str) -> Dict[str, str]:
    expiration = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = {
        "sub": str(user_id),  # Chuyển PydanticObjectId thành chuỗi
        "role": role,
        "email": email,
        "phone": phone,
        "exp": expiration,
        "iat": datetime.utcnow()
    }

    # Tạo JWT token
    token = jwt.encode(payload, secret_key, algorithm=ALGORITHM)
    return token_response(token)


# Hàm giải mã JWT
def decode_jwt(token: str) -> dict:
    try:
        decoded_token = jwt.decode(token, secret_key, algorithms=[ALGORITHM])

        if decoded_token["exp"] < time.time():
            raise HTTPException(status_code=401, detail="Token has expired")

        return decoded_token

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
