# API Benchmark Guide

## Tổng quan
API Benchmark được thiết kế để test hiệu suất của API predict bằng cách gửi nhiều request đồng thời (concurrent requests).

## Endpoint
```
POST /predict/benchmark
```

## Parameters

### Request Body (Form Data)
- `file`: Image file để test (JPG, PNG, etc.)
- `concurrent_requests`: Số lượng request đồng thời (tối đa 50)

### Headers
- `Authorization`: Bearer token (JWT)

## Example Usage

### Sử dụng curl
```bash
curl -X POST "http://localhost:8000/predict/benchmark" \
     -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     -F "file=@test_image.jpg" \
     -F "concurrent_requests=10"
```

### Sử dụng Python requests
```python
import requests

url = "http://localhost:8000/predict/benchmark"
headers = {
    "Authorization": "Bearer YOUR_JWT_TOKEN"
}

files = {
    "file": ("test_image.jpg", open("test_image.jpg", "rb"), "image/jpeg")
}

data = {
    "concurrent_requests": 10
}

response = requests.post(url, headers=headers, files=files, data=data)
print(response.json())
```

### Sử dụng JavaScript/Fetch
```javascript
const formData = new FormData();
formData.append('file', fileInput.files[0]);
formData.append('concurrent_requests', '10');

fetch('/predict/benchmark', {
    method: 'POST',
    headers: {
        'Authorization': 'Bearer YOUR_JWT_TOKEN'
    },
    body: formData
})
.then(response => response.json())
.then(data => console.log(data));
```

## Response Format

```json
{
    "benchmark_info": {
        "timestamp": "2024-01-15T10:30:00.123456",
        "concurrent_requests": 10,
        "total_benchmark_time_ms": 2450.67,
        "file_name": "test_image.jpg",
        "file_size_bytes": 124567
    },
    "performance_metrics": {
        "success_count": 9,
        "failure_count": 1,
        "success_rate_percent": 90.0,
        "throughput_rps": 4.08,
        "response_time_stats_ms": {
            "average": 1200.45,
            "median": 1150.32,
            "minimum": 980.12,
            "maximum": 1850.67,
            "p95": 1780.43,
            "p99": 1820.12
        }
    },
    "detailed_results": {
        "successful_requests": [
            {
                "request_id": 1,
                "status_code": 200,
                "response_time_ms": 1150.32,
                "success": true,
                "error": null,
                "response_size_bytes": 15678
            }
            // ... more results (first 10 only)
        ],
        "failed_requests": [
            {
                "request_id": 8,
                "status_code": 500,
                "response_time_ms": 2000.45,
                "success": false,
                "error": "Internal Server Error",
                "response_size_bytes": 0
            }
        ],
        "all_response_times_ms": [1150.32, 1200.45, ...]
    }
}
```

## Metrics Giải thích

### benchmark_info
- `timestamp`: Thời gian thực hiện benchmark
- `concurrent_requests`: Số request đồng thời đã gửi
- `total_benchmark_time_ms`: Tổng thời gian benchmark (ms)
- `file_name`: Tên file ảnh test
- `file_size_bytes`: Kích thước file ảnh (bytes)

### performance_metrics
- `success_count`: Số request thành công
- `failure_count`: Số request thất bại
- `success_rate_percent`: Tỷ lệ thành công (%)
- `throughput_rps`: Throughput (requests per second)
- `response_time_stats_ms`: Thống kê thời gian response
  - `average`: Thời gian trung bình
  - `median`: Thời gian trung vị
  - `minimum`: Thời gian tối thiểu
  - `maximum`: Thời gian tối đa
  - `p95`: Percentile 95%
  - `p99`: Percentile 99%

### detailed_results
- `successful_requests`: Chi tiết 10 request thành công đầu tiên
- `failed_requests`: Chi tiết tất cả request thất bại
- `all_response_times_ms`: Tất cả thời gian response

## Best Practices

1. **Bắt đầu với số lượng nhỏ**: Test với 5-10 concurrent requests trước
2. **Giám sát tài nguyên**: Theo dõi CPU, RAM khi chạy benchmark
3. **Network latency**: Chạy benchmark từ cùng network để giảm latency
4. **Warmup**: Chạy vài request trước khi benchmark chính thức
5. **Repeat tests**: Chạy nhiều lần để có kết quả ổn định

## Limits và Security

- **Max concurrent requests**: 50 (có thể điều chỉnh trong code)
- **Timeout**: 30 giây cho mỗi request
- **Authentication**: Yêu cầu JWT token hợp lệ
- **File size**: Giới hạn theo setting upload của server

## Troubleshooting

### Lỗi thường gặp

1. **Connection timeout**: Server quá tải, giảm concurrent_requests
2. **401 Unauthorized**: Kiểm tra JWT token
3. **413 Request Entity Too Large**: File ảnh quá lớn
4. **500 Internal Server Error**: Lỗi server, kiểm tra logs

### Tips tối ưu

1. Sử dụng ảnh có kích thước hợp lý (< 5MB)
2. Chạy benchmark khi server ít tải
3. Theo dõi memory usage của YOLO model
4. Cân nhắc sử dụng connection pooling 