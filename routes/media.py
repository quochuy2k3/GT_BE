import cloudinary
import cloudinary.uploader
from fastapi import APIRouter, File, UploadFile
from fastapi.responses import JSONResponse
import os
import uuid
from config.config import Settings

router = APIRouter()

# Get settings
settings = Settings()

cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET,
    secure=True
)

@router.post("/upload-image")
async def upload_image(file: UploadFile = File(...)):
    try:
        # Tạo thư mục 'temp' nếu nó chưa tồn tại
        os.makedirs('temp', exist_ok=True)

        # Lưu tạm file ảnh
        file_location = f"temp/{file.filename}"
        with open(file_location, "wb") as buffer:
            buffer.write(await file.read())

        # Tải lên Cloudinary
        response = cloudinary.uploader.upload(file_location)

        # Trả về URL của hình ảnh đã được upload
        return JSONResponse(content={"url": response["secure_url"]})

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


async def upload_scan_image_to_cloudinary(image_bytes: bytes):
    try:
        # Tạo thư mục 'temp' nếu nó chưa tồn tại
        os.makedirs('temp', exist_ok=True)
        file_location = f"temp/{uuid.uuid4()}.jpg"

        # Write image bytes to file
        with open(file_location, "wb") as buffer:
            buffer.write(image_bytes)

        # Upload image to Cloudinary
        response = cloudinary.uploader.upload(file_location)

        # Return the secure URL as a string
        return response["secure_url"]

    except Exception as e:
        # In case of an error, return an error message
        return str(e)




