from fastapi import APIRouter, HTTPException, Depends, Body
from fastapi.responses import JSONResponse
import google.generativeai as genai
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, Union
from config.jwt_bearer import JWTBearer
from config.config import Settings
import os
import base64
import re
import json
import logging
from datetime import datetime

router = APIRouter()

# Configure the Gemini API
settings = Settings()
api_key = settings.GEMINI_API_KEY 
if api_key:
    genai.configure(api_key=api_key)
else:
    raise ValueError("GEMINI_API_KEY environment variable is not set")

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Vietnamese acne type mapping for better localization
ACNE_TYPE_MAPPING = {
    "blackhead": "Mụn đầu đen",
    "whitehead": "Mụn đầu trắng", 
    "papular": "Mụn sưng đỏ",
    "pustular": "Mụn mủ",
    "nodular": "Mụn bọc",
    "cystic": "Mụn nang",
    "comedonal": "Mụn cám",
    "acne": "Mụn trứng cá"
}

def load_prompt_from_file(prompt_type: str = "default") -> Optional[str]:
    """
    Load specific prompt from markdown file based on prompt type.
    
    Args:
        prompt_type: Type of prompt to load (default, assessment, recommendations, etc.)
    
    Returns:
        Loaded prompt content or None if not found
    """
    try:
        prompt_file_path = os.path.join("docs", "gemini_prompts.md")
        if not os.path.exists(prompt_file_path):
            logger.warning(f"Prompt file not found: {prompt_file_path}")
            return None
            
        with open(prompt_file_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Define section mapping for different prompt types
        section_mapping = {
            "default": r"## Default Skin Analysis Prompt\n(.*?)(?=\n##|\Z)",
            "assessment": r"## Skin Assessment Prompt\n(.*?)(?=\n##|\Z)",
            "safe_recommendations": r"## Safe Recommendations Prompt\n(.*?)(?=\n##|\Z)",
            "medical_disclaimer": r"## Medical Disclaimer\n(.*?)(?=\n##|\Z)"
        }
        
        pattern = section_mapping.get(prompt_type, section_mapping["default"])
        prompt_match = re.search(pattern, content, re.DOTALL)
        
        if prompt_match:
            logger.info(f"Successfully loaded {prompt_type} prompt from file")
            return prompt_match.group(1).strip()
        else:
            logger.warning(f"Section {prompt_type} not found in prompt file")
            return None
            
    except Exception as e:
        logger.error(f"Error loading prompt file: {e}")
        return None

class GeminiRequest(BaseModel):
    image_base64: Optional[str] = None
    class_summary: Dict[str, Dict[str, Any]]
    custom_prompt: Optional[str] = Field(None, description="Custom analysis prompt (optional)")
    analysis_type: Optional[str] = Field("default", description="Type of analysis: default, assessment, safe_recommendations")

    model_config = {
        "json_schema_extra": {
            "example": {
                "image_base64": "base64_encoded_image_string",
                "class_summary": {
                    "blackhead": {"count": 5, "color": "#1E2761"},
                    "papular": {"count": 2, "color": "#FF5722"},
                    "pustular": {"count": 1, "color": "#FF9800"}
                },
                "analysis_type": "safe_recommendations",
                "custom_prompt": "Tập trung vào routine chăm sóc dịu nhẹ"
            }
        }
    }

def fix_base64_padding(b64_string: str) -> str:
    """Fixes base64 string padding if necessary."""
    if not b64_string:
        return b64_string
    
    # Clean the base64 string
    b64_string = b64_string.strip()
    b64_string = re.sub(r'\s+', '', b64_string)
    
    # Remove data URL prefix if present
    if b64_string.startswith('data:image'):
        b64_string = b64_string.split(',', 1)[1] if ',' in b64_string else b64_string
    
    # Add padding if needed
    missing_padding = len(b64_string) % 4
    if missing_padding:
        b64_string += '=' * (4 - missing_padding)
    
    return b64_string

def get_safe_fallback_prompt() -> str:
    """Return a safe, medically appropriate fallback prompt."""
    return """
# Chuyên viên tư vấn chăm sóc da - Đánh giá an toàn

## Vai trò
Bạn là chuyên viên tư vấn chăm sóc da với kinh nghiệm lâu năm, luôn ưu tiên sự an toàn và khuyến khích tham khảo ý kiến chuyên gia y tế.

## Nguyên tắc đánh giá
1. **Quan sát tổng quát**: Mô tả tình trạng da một cách khách quan
2. **Đánh giá mức độ**: Phân loại theo mức độ nhẹ, vừa, nặng
3. **Tư vấn an toàn**: Chỉ đưa ra lời khuyên chăm sóc cơ bản, không kê đơn thuốc
4. **Khuyến cáo y tế**: Luôn khuyên tham khảo bác sĩ da liễu khi cần thiết

## Định dạng JSON trả về (BẮT BUỘC):```json
{
  "tong_quan": "Mô tả tổng quan tình trạng da bằng tiếng Việt",
  "danh_gia_muc_do": "Nhẹ/Vừa/Nặng với giải thích ngắn gọn",
  "chi_tiet_mun": {
    "Tên loại mụn": "Mô tả đặc điểm và vị trí xuất hiện"
  },
  "cham_soc_co_ban": [
    "Bước chăm sóc da hàng ngày an toàn",
    "Thói quen tốt cần duy trì"
  ],
  "luu_y_quan_trong": [
    "Những điều cần tránh để không làm nặng tình trạng",
    "Dấu hiệu cần gặp bác sĩ ngay"
  ],
  "khuyen_cao_y_te": "Lời khuyên về việc tham khảo ý kiến chuyên gia y tế",
  "thong_tin_bo_sung": {
    "do_tin_cay": "Mức độ tin cậy của đánh giá (%)",
    "can_kham_chuyen_khoa": true/false,
    "ly_do_kham": "Lý do nên đi khám nếu cần"
  }
}
```

Hãy phân tích một cách an toàn, khách quan và luôn khuyến khích tham khảo ý kiến chuyên gia y tế khi cần thiết.
"""

def build_enhanced_safe_prompt(
    class_summary: Dict[str, Dict[str, Any]], 
    analysis_type: str = "default",
    custom_prompt: Optional[str] = None
) -> str:
    """Build safe, medically appropriate prompt."""
    
    # Calculate total acne count and create detailed summary
    total_count = 0
    condition_details = []
    
    for condition, details in class_summary.items():
        count = details.get('count', 0)
        total_count += count
        vietnamese_name = ACNE_TYPE_MAPPING.get(condition.lower(), condition.capitalize())
        condition_details.append(f"- **{vietnamese_name}**: {count} vị trí")
    
    # Determine severity level safely
    if total_count < 5:
        severity_note = "ít mụn"
    elif total_count < 15:
        severity_note = "mức độ vừa phải"
    elif total_count < 30:
        severity_note = "khá nhiều mụn"
    else:
        severity_note = "nhiều mụn, cần đặc biệt chú ý"
    
    condition_text = "\n".join(condition_details)
    
    # Load appropriate prompt based on analysis type
    if custom_prompt:
        base_prompt = custom_prompt
        logger.info("Using custom prompt")
    else:
        loaded_prompt = load_prompt_from_file(analysis_type)
        if loaded_prompt:
            base_prompt = loaded_prompt
            logger.info(f"Using {analysis_type} prompt from file")
        else:
            base_prompt = get_safe_fallback_prompt()
            logger.info("Using safe fallback prompt")
    
    # Add medical disclaimer
    medical_disclaimer = load_prompt_from_file("medical_disclaimer")
    if not medical_disclaimer:
        medical_disclaimer = """
**QUAN TRỌNG**: Đây chỉ là đánh giá sơ bộ dựa trên hình ảnh. Không được thay thế cho việc khám và tư vấn trực tiếp từ bác sĩ da liễu. Nếu tình trạng da không cải thiện, có dấu hiệu nhiễm trùng, hoặc bạn có thắc mắc, hãy tham khảo ý kiến bác sĩ chuyên khoa.
"""
    
    enhanced_prompt = f"""{base_prompt}

## Thông tin phân tích hiện tại
**Tổng số vị trí có mụn**: {total_count} ({severity_note})

**Các loại mụn được phát hiện**:
{condition_text}

{medical_disclaimer}

## Yêu cầu cuối cùng
Dựa trên hình ảnh và thông tin trên, hãy đưa ra đánh giá an toàn theo định dạng JSON đã quy định, tập trung vào chăm sóc cơ bản và khuyến cáo y tế phù hợp.
"""
    
    return enhanced_prompt

def parse_safe_response(response_text: str) -> Dict[str, Any]:
    """Parse Gemini response with focus on safe, structured format."""
    try:
        # Extract JSON from response
        json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to find JSON object
            json_pattern = r'\{.*\}'
            json_match = re.search(json_pattern, response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                # Return structured fallback if no JSON found
                return create_safe_fallback_response(response_text)
        
        # Parse JSON
        parsed_response = json.loads(json_str)
        
        # Validate and ensure Vietnamese keys
        if isinstance(parsed_response, dict):
            # Ensure all required Vietnamese keys exist
            required_keys = [
                'tong_quan', 'danh_gia_muc_do', 'chi_tiet_mun', 
                'cham_soc_co_ban', 'luu_y_quan_trong', 'khuyen_cao_y_te'
            ]
            
            # Add missing keys with safe defaults
            for key in required_keys:
                if key not in parsed_response:
                    parsed_response[key] = get_safe_default_value(key)
            
            return {
                "phan_tich": parsed_response,
                "dinh_dang": "json_co_cau_truc",
                "xu_ly_thanh_cong": True
            }
        
        return create_safe_fallback_response(response_text)
        
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning(f"JSON parsing failed: {e}")
        return create_safe_fallback_response(response_text, str(e))

def get_safe_default_value(key: str) -> Any:
    """Return safe default values for missing keys."""
    defaults = {
        'tong_quan': "Cần đánh giá thêm từ chuyên gia da liễu",
        'danh_gia_muc_do': "Cần khám chuyên khoa để đánh giá chính xác",
        'chi_tiet_mun': {"Cần đánh giá": "Tham khảo ý kiến bác sĩ da liễu"},
        'cham_soc_co_ban': ["Vệ sinh da nhẹ nhàng", "Tránh chạm tay lên mặt"],
        'luu_y_quan_trong': ["Không nặn mụn", "Gặp bác sĩ nếu tình trạng xấu đi"],
        'khuyen_cao_y_te': "Nên tham khảo ý kiến bác sĩ da liễu để có phương pháp điều trị phù hợp"
    }
    return defaults.get(key, "Cần tham khảo ý kiến chuyên gia")

def create_safe_fallback_response(response_text: str, error: str = None) -> Dict[str, Any]:
    """Create a safe fallback response structure."""
    return {
        "phan_tich": {
            "tong_quan": "Đã phát hiện một số vị trí có mụn trên da. Cần đánh giá thêm từ chuyên gia để có lời khuyên phù hợp.",
            "danh_gia_muc_do": "Cần khám chuyên khoa để đánh giá chính xác mức độ",
            "chi_tiet_mun": {"Cần đánh giá chuyên sâu": "Tham khảo ý kiến bác sĩ da liễu để xác định chính xác loại mụn và nguyên nhân"},
            "cham_soc_co_ban": [
                "Vệ sinh da mặt nhẹ nhàng 2 lần/ngày",
                "Sử dụng sản phẩm dịu nhẹ, không chứa cồn",
                "Tránh chạm tay lên vùng da có mụn",
                "Giữ gối và khăn mặt sạch sẽ"
            ],
            "luu_y_quan_trong": [
                "Tuyệt đối không nặn mụn bằng tay",
                "Tránh sử dụng sản phẩm quá mạnh mà chưa có sự tư vấn",
                "Theo dõi tình trạng da và ghi chú thay đổi",
                "Gặp bác sĩ ngay nếu có dấu hiệu nhiễm trùng"
            ],
            "khuyen_cao_y_te": "Để có được đánh giá chính xác và phương pháp điều trị an toàn, hiệu quả nhất, bạn nên đặt lịch khám với bác sĩ da liễu.",
            "thong_tin_bo_sung": {
                "do_tin_cay": "70%",
                "can_kham_chuyen_khoa": True,
                "ly_do_kham": "Để có đánh giá chính xác và phương pháp điều trị phù hợp với tình trạng da cụ thể"
            }
        },
        "phan_tich_goc": response_text,
        "dinh_dang": "fallback_an_toan",
        "xu_ly_thanh_cong": False,
        "loi_xu_ly": error
    }

@router.post("/analyze")
async def analyze_with_gemini(
    request_data: GeminiRequest,
    token: str = Depends(JWTBearer())
):
    """
    Analyze skin image with Gemini AI - Safe medical approach.
    
    Args:
        request_data: Contains base64 image, detected acne summary, and analysis type
        token: JWT authentication token
        
    Returns:
        JSONResponse with safe, structured analysis results in Vietnamese
    """
    start_time = datetime.now()
    
    try:
        # Validate required data
        if not request_data.image_base64:
            raise HTTPException(status_code=400, detail="image_base64 là bắt buộc")
        
        try:
            fixed_b64 = fix_base64_padding(request_data.image_base64)
            image_content = base64.b64decode(fixed_b64)
            logger.info(f"Đã xử lý ảnh thành công, kích thước: {len(image_content)} bytes")
        except Exception as decode_err:
            logger.error(f"Lỗi giải mã base64: {decode_err}")
            raise HTTPException(status_code=400, detail=f"Dữ liệu ảnh base64 không hợp lệ: {str(decode_err)}")
        
        # Detect image format
        mime_type = "image/jpeg"  # default
        if image_content.startswith(b'\x89PNG'):
            mime_type = "image/png"
        elif image_content.startswith(b'GIF'):
            mime_type = "image/gif"
        elif image_content.startswith(b'\xff\xd8\xff'):
            mime_type = "image/jpeg"
            
        logger.info(f"Định dạng ảnh: {mime_type}")
        
        # Configure Gemini with conservative settings for medical analysis
        generation_config = genai.types.GenerationConfig(
            temperature=0.1,  # Very low temperature for consistent medical advice
            top_p=0.7,
            top_k=30,
            max_output_tokens=2048,
        )
        
        model = genai.GenerativeModel(
            'gemini-1.5-flash',
            generation_config=generation_config
        )
        
        # Prepare image data
        image_data = {
            "mime_type": mime_type,
            "data": image_content
        }
        
        # Build safe prompt
        safe_prompt = build_enhanced_safe_prompt(
            request_data.class_summary,
            request_data.analysis_type or "default",
            request_data.custom_prompt
        )
        
        logger.info("Đang gửi yêu cầu tới Gemini API")
        
        # Get AI response
        try:
            response = model.generate_content([safe_prompt, image_data])
            logger.info("Đã nhận phản hồi từ Gemini API")
        except Exception as api_error:
            logger.error(f"Lỗi Gemini API: {api_error}")
            raise HTTPException(status_code=503, detail=f"Dịch vụ AI tạm thời không khả dụng: {str(api_error)}")
        
        # Parse response safely
        parsed_result = parse_safe_response(response.text)
        # Prepare final response in Vietnamese
        response_content = {
            "result": parsed_result["phan_tich"],
            "notice": "Kết quả này chỉ mang tính chất tham khảo. Hãy tham khảo ý kiến bác sĩ da liễu để có lời khuyên chính xác nhất."
        }
        
        # Add error info if exists
        if "error" in parsed_result:
            response_content["error"] = parsed_result["error"]
        
        if "original_analysis" in parsed_result:
            response_content["original_analysis"] = parsed_result["original_analysis"]
        
        return JSONResponse(content=response_content)
        
    except HTTPException as he:
        logger.error(f"HTTP Exception: {he.detail}")
        raise he
    except Exception as e:
        processing_time = (datetime.now() - start_time).total_seconds()
        logger.error(f"Unexpected error after {processing_time:.2f}s: {e}")
        
        error_detail = {
            "error_type": type(e).__name__,
            "error_message": str(e),
            "status": "failed",
            "processing_time": round(processing_time, 2),
            "time": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        }
        raise HTTPException(status_code=500, detail=error_detail)
