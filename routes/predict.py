from bson import ObjectId
from fastapi import APIRouter, HTTPException, Depends, Body,BackgroundTasks
from ultralytics import YOLO

from typing import List
from beanie import PydanticObjectId

from config.jwt_bearer import JWTBearer
from config.jwt_handler import decode_jwt
from models.routine import Routine, Day
from schemas.routine import RoutineSchema, SessionSchema, DaySchema, DayResponseSchema, RoutineUpdateSchema, \
    RoutineUpdatePushToken
from service.routine_service import cron_notification
from fastapi import APIRouter, UploadFile, File
from fastapi.responses import JSONResponse
from PIL import Image, ImageDraw, ImageOps
import io
import base64
from service.tracker_service import tracker_on_day
router = APIRouter()


model = YOLO("./models_ai/yolov8.pt")

@router.post("")
async def predict_image(
        file: UploadFile = File(...),
        background_tasks: BackgroundTasks = BackgroundTasks(),
        token: str = Depends(JWTBearer())
):
    contents = await file.read()
    image = Image.open(io.BytesIO(contents)).convert("RGB")

    original_image = image.copy()


    results = model.predict(image)
    boxes = results[0].boxes
    class_names = model.names

    draw = ImageDraw.Draw(original_image, 'RGBA')

    skin_condition_colors = {
        'blackhead': ('#1E2761', '#1E276180'),  # Deep blue
        'papular': ('#FF5722', '#FF572280'),    # Orange-red
        'purulent': ('#FFEB3B', '#FFEB3B80')    # Bright yellow
    }

    # Default colors for any other classes that might be present
    default_colors = [
        ('#E63946', '#E6394680'),  # Red
        ('#2ECC71', '#2ECC7180'),  # Green
        ('#3498DB', '#3498DB80'),  # Blue
        ('#9B59B6', '#9B59B680'),  # Purple
        ('#1ABC9C', '#1ABC9C80'),  # Teal
        ('#F39C12', '#F39C1280')   # Orange
    ]

    class_color_map = {}
    default_color_index = 0

    class_summary = {}

    detections = []
    for box in boxes:
        cls = int(box.cls[0])
        class_name = class_names[cls]
        conf = float(box.conf[0])
        xyxy = box.xyxy[0].tolist()

        x1, y1, x2, y2 = map(int, xyxy)

        center_x = (x1 + x2) // 2
        center_y = (y1 + y2) // 2
        radius = max(min(x2 - x1, y2 - y1) // 2, 15)

        detections.append({
            "class": class_name,
            "confidence": round(conf, 2),
            "bbox": [x1, y1, x2, y2]
        })

        if class_name in skin_condition_colors:
            outline_color, fill_color = skin_condition_colors[class_name]
        else:
            if class_name not in class_color_map:
                class_color_map[class_name] = default_colors[default_color_index % len(default_colors)]
                default_color_index += 1

            outline_color, fill_color = class_color_map[class_name]

        if class_name not in class_summary:
            class_summary[class_name] = {
                "count": 1,
                "color": outline_color
            }
        else:
            class_summary[class_name]["count"] += 1

        draw.ellipse(
            [(center_x - radius, center_y - radius),
             (center_x + radius, center_y + radius)],
            fill=fill_color,
            outline=outline_color,
            width=3
        )

        outer_radius = radius + 5
        draw.ellipse(
            [(center_x - outer_radius, center_y - outer_radius),
             (center_x + outer_radius, center_y + outer_radius)],
            fill=None,
            outline=outline_color + "40",
            width=2
        )

    buffered = io.BytesIO()
    original_image.save(buffered, format="JPEG", quality=100)
    img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
    image_bytes = buffered.getvalue()
    # Schedule the background task to save results
    background_tasks.add_task(
        tracker_on_day,
        token,
        buffered.getvalue(),
        class_summary
    )

    response_data = {
        "class_summary": class_summary,
        "image": img_base64
    }

    return JSONResponse(content=response_data)
