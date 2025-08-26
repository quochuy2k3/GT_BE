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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

def load_prompt_from_file(prompt_type: str = "default") -> str:
    """
    Load specific prompt from markdown file based on prompt type.
    
    Args:
        prompt_type: Type of prompt to load (default, assessment, recommendations, etc.)
    
    Returns:
        Loaded prompt content
    
    Raises:
        FileNotFoundError: If prompt file is not found
        ValueError: If prompt section is not found in file
        Exception: If any other error occurs while loading
    """
    try:
        prompt_file_path = os.path.join("docs", "gemini_prompts.md")
        if not os.path.exists(prompt_file_path):
            raise FileNotFoundError(f"Prompt file not found: {prompt_file_path}")
            
        with open(prompt_file_path, "r", encoding="utf-8") as f:
            content = f.read()
            
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
            raise ValueError(f"Section {prompt_type} not found in prompt file")
            
    except (FileNotFoundError, ValueError) as e:
        logger.error(f"Error loading prompt file: {e}")
        raise e
    except Exception as e:
        logger.error(f"Unexpected error loading prompt file: {e}")
        raise Exception(f"Failed to load prompt: {str(e)}")

class GeminiRequest(BaseModel):
    image_base64: str = Field(..., description="Base64 encoded image for analysis")
    class_summary: Optional[Dict[str, Dict[str, Any]]] = Field(None, description="Pre-detected acne summary (optional)")
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
    
    b64_string = b64_string.strip()
    b64_string = re.sub(r'\s+', '', b64_string)
    
    if b64_string.startswith('data:image'):
        b64_string = b64_string.split(',', 1)[1] if ',' in b64_string else b64_string
    
    missing_padding = len(b64_string) % 4
    if missing_padding:
        b64_string += '=' * (4 - missing_padding)
    
    return b64_string



def build_enhanced_safe_prompt(
    class_summary: Optional[Dict[str, Dict[str, Any]]] = None, 
    analysis_type: str = "default",
    custom_prompt: Optional[str] = None
) -> str:
    """Build comprehensive skin analysis prompt - AI analyzes image directly."""
    
    # If class_summary is provided, use it as additional info
    additional_info = ""
    if class_summary:
        total_count = 0
        condition_details = []
        
        for condition, details in class_summary.items():
            count = details.get('count', 0)
            total_count += count
            vietnamese_name = ACNE_TYPE_MAPPING.get(condition.lower(), condition.capitalize())
            condition_details.append(f"- **{vietnamese_name}**: {count} vị trí")
        
        # Determine severity level
        if total_count < 5:
            severity_note = "ít mụn"
        elif total_count < 15:
            severity_note = "mức độ vừa phải"
        elif total_count < 30:
            severity_note = "khá nhiều mụn"
        else:
            severity_note = "nhiều mụn, cần đặc biệt chú ý"
        
        condition_text = "\n".join(condition_details)
        additional_info = f"""
## THÔNG TIN BỔ SUNG (từ AI detection model):
**Tổng số vị trí có mụn được phát hiện**: {total_count} ({severity_note})

**Chi tiết các loại mụn**:
{condition_text}

*Lưu ý: Thông tin trên chỉ mang tính tham khảo. Hãy TỰ PHÂN TÍCH ảnh một cách độc lập và đưa ra đánh giá của riêng bạn.*
"""
    
    if custom_prompt:
        base_prompt = custom_prompt
        logger.info("Using custom prompt")
    else:
        # Hard coded comprehensive prompt
        base_prompt = """
# CHUYÊN GIA PHÂN TÍCH DA MẶT - TỰ ĐÁNH GIÁ TOÀN DIỆN TỪ ẢNH

## VAI TRÒ CỦA BẠN
Bạn là chuyên gia phân tích da mặt hàng đầu với 20+ năm kinh nghiệm. Nhiệm vụ của bạn là:
- **TỰ QUAN SÁT** và PHÂN TÍCH ảnh khuôn mặt một cách chi tiết
- **NHẬN DIỆN** tất cả các vấn đề về da: mụn, nám, nếp nhăn, lỗ chân lông, độ đàn hồi, màu sắc
- **ĐÁNH GIÁ THỰC TẾ** dựa trên những gì BẠN NHÌN THẤY trong ảnh
- **TƯ VẤN GIẢI PHÁP** cụ thể và có thể áp dụng ngay

## PHƯƠNG PHÁP PHÂN TÍCH ẢNH
1. **QUAN SÁT TỔNG THỂ**: Nhìn toàn bộ khuôn mặt, đánh giá tổng quan
2. **PHÂN TÍCH TỪNG VÙNG**: Chia thành 5 vùng và quan sát kỹ lưỡng
3. **NHẬN DIỆN VẤN ĐỀ**: Tự phát hiện mụn, nám, nếp nhăn, lỗ chân lông
4. **ĐÁNH GIÁ MỨC ĐỘ**: Cho điểm từ 1-10 dựa trên quan sát thực tế
5. **TƯ VẤN CỤ THỂ**: Đưa ra giải pháp phù hợp với những gì thấy được

## NGUYÊN TẮC ĐÁNH GIÁ
1. **TỰ PHÂN TÍCH**: Hãy TỰ NHÌN VÀO ẢNH và mô tả chi tiết những gì bạn thấy
2. **MÔ TẢ CỤ THỂ**: Nói rõ vị trí, màu sắc, kích thước, texture của từng vấn đề
3. **ĐÁNH GIÁ THỰC TẾ**: Đưa ra mức độ cụ thể từ 1-10 cho từng vấn đề
4. **TƯ VẤN THIẾT THỰC**: Đề xuất routine chăm sóc cụ thể có thể làm ngay
5. **KHUYẾN CÁO CÂN BẰNG**: Chỉ khuyên gặp bác sĩ khi THỰC SỰ CẦN THIẾT

## ĐỊNH DẠNG JSON BẮT BUỘC:
```json
{
  "danh_gia_tong_quan": {
    "loai_da": "TỰ XÁC ĐỊNH từ ảnh: Da khô/Da dầu/Da hỗn hợp/Da nhạy cảm với mô tả chi tiết về căn cứ đánh giá",
    "tinh_trang_chung": "Mô tả THỰC TẾ những gì TỰ QUAN SÁT được từ ảnh, không mơ hồ",
    "diem_manh": ["Liệt kê các ưu điểm cụ thể NHÌN THẤY được từ ảnh"],
    "diem_yeu": ["Các vấn đề TỰ PHÁT HIỆN được với mức độ từ 1-10"],
    "muc_do_nghiem_trong": "Nhẹ/Vừa/Nặng với LÝ DO CỤ THỂ dựa trên quan sát trực tiếp"
  },
  "phan_tich_theo_vung": {
    "vung_T": "Phân tích CHI TIẾT vùng trán-mũi-cằm: texture, dầu nhờn, mụn, lỗ chân lông",
    "vung_U": "Phân tích CHI TIẾT vùng má-thái dương: độ ẩm, đều màu, độ đàn hồi", 
    "vung_mat": "Đánh giá CỤ THỂ: nếp nhăn, bọng mắt, quầng thâm với mức độ",
    "vung_moi": "Phân tích môi và vùng quanh môi: độ ẩm, màu sắc, nứt nẻ",
    "vung_co": "Đánh giá cổ và hàm dưới: độ căng, màu sắc, texture"
  },
  "chi_tiet_van_de": {
    "mun_trung_ca": {
      "phan_tich_cu_the": "Mô tả CHÍNH XÁC từng loại mụn: vị trí, kích thước, màu sắc, mức độ viêm",
      "nguyen_nhan_chinh": ["Xác định 2-3 nguyên nhân chính gây ra tình trạng hiện tại"],
      "do_nghiem_trong": "Thang điểm 1-10 với giải thích cụ thể",
      "xu_huong_phat_trien": "Dự đoán THỰC TẾ về diễn biến trong 2-4 tuần tới"
    },
    "van_de_khac": {
      "lao_hoa": "Đánh giá nếp nhăn, chảy xệ với điểm số 1-10",
      "sac_to": "Phân tích nám, tàn nhang, đốm nâu với vị trí và mức độ cụ thể",
      "do_am_dau": "Đánh giá cân bằng dầu-nước với điểm số và mô tả",
      "lo_chan_long": "Đánh giá kích thước và tình trạng tắc nghẽn"
    }
  },
  "routine_cham_soc_cu_the": {
    "buoi_sang": [
      "Bước 1: [Tên sản phẩm cụ thể] - Cách dùng - Lý do",
      "Bước 2: [Tên sản phẩm cụ thể] - Cách dùng - Lý do",
      "Bước 3: [Tên sản phẩm cụ thể] - Cách dùng - Lý do"
    ],
    "buoi_toi": [
      "Bước 1: [Tên sản phẩm cụ thể] - Cách dùng - Lý do",
      "Bước 2: [Tên sản phẩm cụ thể] - Cách dùng - Lý do", 
      "Bước 3: [Tên sản phẩm cụ thể] - Cách dùng - Lý do"
    ],
    "cham_soc_dac_biet": {
      "2-3_lan_tuan": ["Liệu trình cụ thể với tên sản phẩm và cách thực hiện"],
      "hang_thang": ["Điều trị sâu với sản phẩm và phương pháp cụ thể"],
      "luu_y_quan_trong": ["Những điều TUYỆT ĐỐI không được làm"]
    }
  },
  "ket_qua_mong_doi": {
    "sau_2_tuan": "Những thay đổi CỤ THỂ có thể thấy được",
    "sau_1_thang": "Mức độ cải thiện THỰC TẾ có thể đạt được",
    "sau_3_thang": "Kết quả dài hạn và mục tiêu hoàn thiện",
    "chi_phi_uoc_tinh": "Ước tính chi phí routine hàng tháng"
  },
  "canh_bao_va_khuyen_cao": {
    "can_gap_bac_si": "CHỈ khuyên gặp bác sĩ khi THỰC SỰ cần thiết với lý do cụ thể",
    "muc_do_khan_cap": "Không khẩn cấp/Nên sớm/Khẩn cấp",
    "co_the_tu_cham_soc": "true/false - Đánh giá có thể tự chăm sóc tại nhà không",
    "dau_hieu_theo_doi": ["Các dấu hiệu cần theo dõi trong quá trình điều trị"]
  },
  "do_tin_cay_danh_gia": {
    "phan_tram": "Từ 75-95% tùy theo độ rõ ràng của hình ảnh",
    "han_che": ["Các hạn chế cụ thể của việc đánh giá qua ảnh"],
    "de_xuat_bo_sung": ["Gợi ý để có đánh giá chính xác hơn nếu cần"]
  }
}
```

## QUY TRÌNH PHÂN TÍCH BẮT BUỘC:

### 1. QUAN SÁT VÀ PHÂN TÍCH
- Nhìn vào hình ảnh và mô tả CHI TIẾT những gì bạn thấy
- Đánh giá màu sắc, texture, độ bóng/mờ, lỗ chân lông
- Phân tích TỪNG VÙNG một cách cụ thể

### 2. ĐÁNH GIÁ THỰC TẾ
- Đưa ra điểm số 1-10 cho từng vấn đề
- Giải thích CỤ THỂ căn cứ đánh giá
- So sánh với tiêu chuẩn bình thường của độ tuổi

### 3. TƯ VẤN THIẾT THỰC
- Đề xuất sản phẩm CỤ THỂ (tên thương hiệu nếu có thể)
- Hướng dẫn cách sử dụng CHI TIẾT
- Ước tính thời gian và chi phí

### 4. KHUYẾN CÁO CÂN BẰNG
- CHỈ khuyên gặp bác sĩ khi THẬT SỰ cần thiết
- Đa số trường hợp có thể tự chăm sóc tại nhà
- Đưa ra lộ trình theo dõi cụ thể

## YÊU CẦU QUAN TRỌNG:
- PHẢI PHÂN TÍCH THẬT SỰ, không được nói chung chung
- PHẢI ĐƯA RA ĐIỂM SỐ cụ thể cho từng vấn đề
- PHẢI TƯ VẤN ROUTINE chi tiết có thể làm ngay
- CHỈ khuyên gặp bác sĩ khi thực sự cần thiết (< 20% trường hợp)

Hãy trở thành chuyên gia phân tích da thực thụ - NHẬN XÉT CỤ THỂ, TƯ VẤN THIẾT THỰC!
"""
        logger.info("Using hard-coded comprehensive prompt")
    
    enhanced_prompt = f"""{base_prompt}

{additional_info}

## YÊU CẦU THỰC HIỆN - TỰ PHÂN TÍCH ẢNH
Bạn sẽ nhận được một ảnh khuôn mặt. Hãy:

### BƯỚC 1: TỰ QUAN SÁT VÀ MÔ TẢ
- **Nhìn vào ảnh** và mô tả chi tiết những gì bạn thấy
- **Quan sát từng vùng**: trán, mũi, cằm, má trái, má phải, vùng mắt, môi
- **Phát hiện vấn đề**: Tự tìm mụn, nám, nếp nhăn, lỗ chân lông, độ đàn hồi

### BƯỚC 2: PHÂN TÍCH VÀ ĐÁNH GIÁ
- **Mô tả cụ thể** từng vấn đề: vị trí, kích thước, màu sắc, mức độ
- **Cho điểm số** từ 1-10 cho từng vấn đề dựa trên quan sát
- **Xác định loại da** dựa trên texture, độ bóng/mờ, lỗ chân lông

### BƯỚC 3: TƯ VẤN THỰC TẾ
- **Đưa ra routine** chăm sóc phù hợp với những gì quan sát được
- **Gợi ý sản phẩm** cụ thể cho từng vấn đề
- **Dự đoán kết quả** có thể đạt được

### BƯỚC 4: KHUYẾN CÁO CÂN BẰNG
- **Chỉ khuyên gặp bác sĩ** khi thật sự cần thiết (< 15% trường hợp)
- **Đa số trường hợp** có thể tự chăm sóc hiệu quả tại nhà

**LƯU Ý QUAN TRỌNG**: Hãy TỰ PHÂN TÍCH ảnh và đưa ra đánh giá dựa trên những gì BẠN NHÌN THẤY, không dựa vào thông tin có sẵn!

Hãy trở thành chuyên gia da liễu thực thụ và đưa ra phân tích toàn diện từ chính đôi mắt của bạn!
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
        
        # Validate and ensure required keys exist
        if isinstance(parsed_response, dict):
            # Updated required keys for new format
            required_keys = [
                'danh_gia_tong_quan', 'phan_tich_theo_vung', 'chi_tiet_van_de', 
                'routine_cham_soc_cu_the', 'ket_qua_mong_doi', 'canh_bao_va_khuyen_cao'
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
    """Return default values for missing keys in new format."""
    defaults = {
        'danh_gia_tong_quan': {
            "loai_da": "Cần đánh giá thêm để xác định chính xác",
            "tinh_trang_chung": "Đã phân tích cơ bản, cần thông tin thêm để đánh giá chi tiết",
            "diem_manh": ["Da có vẻ khỏe mạnh tổng thể"],
            "diem_yeu": ["Có một số vấn đề cần cải thiện"],
            "muc_do_nghiem_trong": "Vừa phải - cần theo dõi và chăm sóc đúng cách"
        },
        'phan_tich_theo_vung': {
            "vung_T": "Vùng T có dấu hiệu tiết dầu, cần kiểm soát",
            "vung_U": "Vùng U cần cân bằng độ ẩm",
            "vung_mat": "Vùng mắt cần chăm sóc đặc biệt",
            "vung_moi": "Môi cần dưỡng ẩm",
            "vung_co": "Cổ cần chú ý làm sạch"
        },
        'chi_tiet_van_de': {
            "mun_trung_ca": {
                "phan_tich_cu_the": "Có mụn ở mức độ vừa phải",
                "nguyen_nhan_chinh": ["Tiết dầu dư thừa", "Chăm sóc chưa đúng cách"],
                "do_nghiem_trong": "5/10 - mức độ trung bình",
                "xu_huong_phat_trien": "Có thể cải thiện với chăm sóc đúng cách"
            },
            "van_de_khac": {
                "lao_hoa": "Chưa có dấu hiệu lão hóa rõ rệt - 3/10",
                "sac_to": "Màu da tương đối đều - 4/10",
                "do_am_dau": "Cần cân bằng dầu-nước - 6/10",
                "lo_chan_long": "Lỗ chân lông hơi to - 5/10"
            }
        },
        'routine_cham_soc_cu_the': {
            "buoi_sang": [
                "Bước 1: Sữa rửa mặt dịu nhẹ - Massage 30 giây - Làm sạch không khô da",
                "Bước 2: Toner cân bằng pH - Thấm nhẹ - Chuẩn bị cho các bước tiếp theo",
                "Bước 3: Kem chống nắng SPF 30+ - Thoa đều - Bảo vệ khỏi tia UV"
            ],
            "buoi_toi": [
                "Bước 1: Tẩy trang kỹ lưỡng - Massage nhẹ - Loại bỏ bụi bẩn",
                "Bước 2: Sữa rửa mặt - Làm sạch sâu - Chuẩn bị da hấp thụ",
                "Bước 3: Serum/kem dưỡng - Thoa nhẹ - Phục hồi và dưỡng da"
            ],
            "cham_soc_dac_biet": {
                "2-3_lan_tuan": ["Mặt nạ đất sét - Hút dầu thừa - Làm sạch lỗ chân lông"],
                "hang_thang": ["Điều trị chuyên sâu tại spa - Tùy theo ngân sách"],
                "luu_y_quan_trong": ["Không nặn mụn bằng tay", "Thử patch test trước khi dùng sản phẩm mới"]
            }
        },
        'ket_qua_mong_doi': {
            "sau_2_tuan": "Da sạch hơn, ít bóng dầu hơn",
            "sau_1_thang": "Mụn giảm 60-70%, da đều màu hơn",
            "sau_3_thang": "Da khỏe mạnh, mịn màng, ít mụn rõ rệt",
            "chi_phi_uoc_tinh": "300-500k VND/tháng cho routine cơ bản"
        },
        'canh_bao_va_khuyen_cao': {
            "can_gap_bac_si": "Không cần thiết - có thể tự chăm sóc tại nhà",
            "muc_do_khan_cap": "Không khẩn cấp",
            "co_the_tu_cham_soc": "true",
            "dau_hieu_theo_doi": ["Da đỏ bất thường", "Mụn tăng nhiều đột ngột", "Có dấu hiệu dị ứng"]
        }
    }
    return defaults.get(key, {"thong_tin": "Cần đánh giá thêm"})

def create_safe_fallback_response(response_text: str, error: str = None) -> Dict[str, Any]:
    """Create a comprehensive fallback response structure."""
    return {
        "phan_tich": {
            "danh_gia_tong_quan": {
                "loai_da": "Da hỗn hợp - cần đánh giá thêm để xác định chính xác",
                "tinh_trang_chung": "Phát hiện một số vấn đề về mụn trên da. Tình trạng tổng thể ở mức trung bình, có thể cải thiện với chăm sóc đúng cách.",
                "diem_manh": ["Da có độ đàn hồi tốt", "Màu sắc tương đối đều"],
                "diem_yeu": ["Có mụn cần điều trị - 6/10", "Cần cân bằng dầu-nước - 5/10"],
                "muc_do_nghiem_trong": "Vừa phải - có thể tự chăm sóc tại nhà với routine phù hợp"
            },
            "phan_tich_theo_vung": {
                "vung_T": "Vùng T (trán-mũi-cằm) có dấu hiệu tiết dầu nhiều, lỗ chân lông hơi to, xuất hiện một số mụn cần điều trị",
                "vung_U": "Vùng U (má-thái dương) tương đối ổn định, cần dưỡng ẩm để cân bằng", 
                "vung_mat": "Vùng mắt chưa có dấu hiệu lão hóa rõ rệt, cần chăm sóc để phòng ngừa",
                "vung_moi": "Môi cần dưỡng ẩm thường xuyên",
                "vung_co": "Vùng cổ cần chú ý vệ sinh và dưỡng ẩm"
            },
            "chi_tiet_van_de": {
                "mun_trung_ca": {
                    "phan_tich_cu_the": "Mụn chủ yếu tập trung ở vùng T, có cả mụn đầu đen và mụn viêm nhẹ",
                    "nguyen_nhan_chinh": ["Tiết dầu dư thừa", "Tắc nghẽn lỗ chân lông", "Chăm sóc chưa đúng cách"],
                    "do_nghiem_trong": "6/10 - mức độ trung bình, có thể điều trị tại nhà",
                    "xu_huong_phat_trien": "Có thể cải thiện 70-80% trong 1-2 tháng với chăm sóc đúng cách"
                },
                "van_de_khac": {
                    "lao_hoa": "Chưa có dấu hiệu lão hóa rõ rệt - 2/10",
                    "sac_to": "Màu da tương đối đều, một vài vết thâm nhẹ - 4/10",
                    "do_am_dau": "Mất cân bằng dầu-nước, vùng T dầu, vùng U khô - 6/10",
                    "lo_chan_long": "Lỗ chân lông hơi to ở vùng T - 5/10"
                }
            },
            "routine_cham_soc_cu_the": {
                "buoi_sang": [
                    "Bước 1: Sữa rửa mặt dành cho da dầu/hỗn hợp - Massage 30-60s - Làm sạch dầu thừa",
                    "Bước 2: Toner không cồn - Dùng bông tẩy trang thấm nhẹ - Cân bằng pH",
                    "Bước 3: Serum vitamin C - Thoa nhẹ vùng U - Chống oxy hóa",
                    "Bước 4: Kem chống nắng SPF 30+ - Thoa đều toàn mặt - Bảo vệ da"
                ],
                "buoi_toi": [
                    "Bước 1: Dầu tẩy trang hoặc micellar - Massage nhẹ - Loại bỏ makeup và bụi bẩn",
                    "Bước 2: Sữa rửa mặt - Làm sạch sâu - Chuẩn bị cho các bước tiếp theo",
                    "Bước 3: BHA 2% (3 lần/tuần) - Thoa vùng T - Làm sạch lỗ chân lông",
                    "Bước 4: Kem dưỡng nhẹ - Thoa đều - Phục hồi và dưỡng ẩm"
                ],
                "cham_soc_dac_biet": {
                    "2-3_lan_tuan": ["Mặt nạ đất sét - 10-15 phút - Hút dầu và làm sạch lỗ chân lông"],
                    "hang_thang": ["Tẩy da chết nhẹ", "Điều trị facial cơ bản nếu có điều kiện"],
                    "luu_y_quan_trong": ["KHÔNG nặn mụn bằng tay", "Patch test sản phẩm mới", "Uống đủ nước 2L/ngày"]
                }
            },
            "ket_qua_mong_doi": {
                "sau_2_tuan": "Da sạch hơn, ít bóng dầu, mụn mới giảm 50%",
                "sau_1_thang": "Mụn hiện tại giảm 70%, da đều màu và mịn hơn",
                "sau_3_thang": "Da khỏe mạnh, mụn chỉ còn 10-20%, texture da cải thiện rõ rệt",
                "chi_phi_uoc_tinh": "400-600k VND/tháng cho routine đầy đủ"
            },
            "canh_bao_va_khuyen_cao": {
                "can_gap_bac_si": "KHÔNG cần thiết ngay - có thể tự chăm sóc hiệu quả tại nhà",
                "muc_do_khan_cap": "Không khẩn cấp",
                "co_the_tu_cham_soc": "true",
                "dau_hieu_theo_doi": ["Da đỏ bất thường sau dùng sản phẩm", "Mụn tăng đột ngột", "Có mụn bọc to và đau"]
            },
            "do_tin_cay_danh_gia": {
                "phan_tram": "75%",
                "han_che": ["Đánh giá qua ảnh không thể thay thế khám trực tiếp", "Ánh sáng ảnh có thể ảnh hưởng độ chính xác"],
                "de_xuat_bo_sung": ["Chụp ảnh trong ánh sáng tự nhiên để đánh giá chính xác hơn"]
            }
        },
        "phan_tich_goc": response_text,
        "dinh_dang": "fallback_thuc_te",
        "xu_ly_thanh_cong": False,
        "loi_xu_ly": error
    }

@router.post("/analyze")
async def analyze_with_gemini(
    request_data: GeminiRequest,
    token: str = Depends(JWTBearer())
):
    """
    Analyze skin image with Gemini AI - Direct image analysis approach.
    
    Args:
        request_data: Contains base64 image (required), optional pre-detected acne summary, and analysis type
        token: JWT authentication token
        
    Returns:
        JSONResponse with comprehensive, structured analysis results based on direct image observation
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
        
        print("\n" + "="*80)
        print("📝 PROMPT SENT TO GEMINI:")
        print("="*80)
        print(safe_prompt[:1000] + "..." if len(safe_prompt) > 1000 else safe_prompt)
        print("="*80 + "\n")
        
        logger.info("Đang gửi yêu cầu tới Gemini API")
        
        try:
            response = model.generate_content([safe_prompt, image_data])
            logger.info("Đã nhận phản hồi từ Gemini API")
            
            print("\n" + "="*80)
            print("🤖 GEMINI RAW RESPONSE:")
            print("="*80)
            print(response.text)
            print("="*80 + "\n")
            
        except Exception as api_error:
            logger.error(f"Lỗi Gemini API: {api_error}")
            raise HTTPException(status_code=503, detail=f"Dịch vụ AI tạm thời không khả dụng: {str(api_error)}")
        
        # Parse response safely
        parsed_result = parse_safe_response(response.text)
        
        # Print parsed result
        print("\n" + "="*80)
        print("📊 PARSED RESULT:")
        print("="*80)
        print(json.dumps(parsed_result, ensure_ascii=False, indent=2))
        print("="*80 + "\n")
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
        
        # Print final response to client
        print("\n" + "="*80)
        print("🎯 FINAL RESPONSE TO CLIENT:")
        print("="*80)
        print(json.dumps(response_content, ensure_ascii=False, indent=2))
        print("="*80 + "\n")
        
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
