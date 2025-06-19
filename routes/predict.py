from bson import ObjectId
from fastapi import APIRouter, HTTPException, Depends, Body,BackgroundTasks
from ultralytics import YOLO
import asyncio
import httpx
import statistics
import time
from datetime import datetime
from typing import List
from beanie import PydanticObjectId
from monitoring.fastapi_metrics import increment_image_prediction, record_model_inference_time

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
    import time
    start_time = time.time()
    
    contents = await file.read()
    image = Image.open(io.BytesIO(contents)).convert("RGB")

    original_image = image.copy()

    results = model.predict(image)
    
    # Record inference time
    inference_time = time.time() - start_time
    record_model_inference_time(inference_time)
    increment_image_prediction()  # Increment prediction counter
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


@router.post("/benchmark")
async def benchmark_predict_api(
        file: UploadFile = File(...),
        concurrent_requests: int = Body(..., description="Number of concurrent requests to send"),
        token: str = Depends(JWTBearer())
):
    """
    Benchmark API endpoint to test predict API performance with concurrent requests
    
    Args:
        file: Image file to test with
        concurrent_requests: Number of concurrent requests to send (max 50 for safety)
        token: JWT token for authentication
    
    Returns:
        Benchmark statistics including response times, success rate, etc.
    """
    
    # Validate concurrent_requests limit for safety
    if concurrent_requests > 50:
        raise HTTPException(status_code=400, detail="Maximum 50 concurrent requests allowed")
    
    if concurrent_requests < 1:
        raise HTTPException(status_code=400, detail="Minimum 1 request required")
    
    # Read file content once
    file_content = await file.read()
    
    # Get the base URL for making HTTP requests
    base_url = "http://localhost:8000"  # You can make this configurable
    predict_url = f"{base_url}/v1/predict"
    headers = {"Authorization": f"Bearer {token}"}
    
    async def send_single_request(session: httpx.AsyncClient, request_id: int):
        """Send a single HTTP request to predict endpoint and measure response time"""
        start_time = time.time()
        try:
            # Prepare file data for this request
            files = {"file": (file.filename, io.BytesIO(file_content), file.content_type)}
            
            # Make HTTP request to predict endpoint
            response = await session.post(
                predict_url,
                files=files,
                headers=headers,
                timeout=60.0  # 60 second timeout for YOLO processing
            )
            
            end_time = time.time()
            response_time = (end_time - start_time) * 1000  # Convert to milliseconds
            
            return {
                "request_id": request_id,
                "status_code": response.status_code,
                "response_time_ms": response_time,
                "success": response.status_code == 200,
                "error": None if response.status_code == 200 else response.text,
                "response_size_bytes": len(response.content) if response.status_code == 200 else 0
            }
            
        except Exception as e:
            end_time = time.time()
            response_time = (end_time - start_time) * 1000
            
            return {
                "request_id": request_id,
                "status_code": 0,
                "response_time_ms": response_time,
                "success": False,
                "error": str(e),
                "response_size_bytes": 0
            }
    
    # Start benchmark
    benchmark_start_time = time.time()
    
    # Create HTTP client with connection pooling
    async with httpx.AsyncClient(
        limits=httpx.Limits(max_keepalive_connections=20, max_connections=100),
        timeout=httpx.Timeout(60.0)
    ) as client:
        # Create tasks for concurrent requests
        tasks = [
            send_single_request(client, i+1) 
            for i in range(concurrent_requests)
        ]
        
        # Execute all requests concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
    
    benchmark_end_time = time.time()
    total_benchmark_time = (benchmark_end_time - benchmark_start_time) * 1000  # milliseconds
    
    # Process results
    successful_requests = []
    failed_requests = []
    all_response_times = []
    
    for result in results:
        if isinstance(result, Exception):
            failed_requests.append({
                "error": str(result),
                "success": False
            })
        else:
            all_response_times.append(result["response_time_ms"])
            if result["success"]:
                successful_requests.append(result)
            else:
                failed_requests.append(result)
    
    # Calculate statistics
    success_count = len(successful_requests)
    failure_count = len(failed_requests)
    success_rate = (success_count / concurrent_requests) * 100
    
    # Response time statistics
    if all_response_times:
        avg_response_time = statistics.mean(all_response_times)
        median_response_time = statistics.median(all_response_times)
        min_response_time = min(all_response_times)
        max_response_time = max(all_response_times)
        
        # Calculate percentiles
        sorted_times = sorted(all_response_times)
        p95_response_time = sorted_times[int(0.95 * len(sorted_times))]
        p99_response_time = sorted_times[int(0.99 * len(sorted_times))]
    else:
        avg_response_time = median_response_time = min_response_time = max_response_time = 0
        p95_response_time = p99_response_time = 0
    
    # Calculate throughput (requests per second)
    throughput = concurrent_requests / (total_benchmark_time / 1000) if total_benchmark_time > 0 else 0
    
    benchmark_stats = {
        "benchmark_info": {
            "timestamp": datetime.now().isoformat(),
            "concurrent_requests": concurrent_requests,
            "total_benchmark_time_ms": round(total_benchmark_time, 2),
            "file_name": file.filename,
            "file_size_bytes": len(file_content)
        },
        "performance_metrics": {
            "success_count": success_count,
            "failure_count": failure_count,
            "success_rate_percent": round(success_rate, 2),
            "throughput_rps": round(throughput, 2),
            "response_time_stats_ms": {
                "average": round(avg_response_time, 2),
                "median": round(median_response_time, 2),
                "minimum": round(min_response_time, 2),
                "maximum": round(max_response_time, 2),
                "p95": round(p95_response_time, 2),
                "p99": round(p99_response_time, 2)
            }
        },
        "detailed_results": {
            "successful_requests": successful_requests[:10],  # Show first 10 for brevity
            "failed_requests": failed_requests,
            "all_response_times_ms": all_response_times
        }
    }
    
    return JSONResponse(content=benchmark_stats)
