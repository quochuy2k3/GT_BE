# FastAPI Monitoring với Grafana & Prometheus

## Tổng quan
Setup này sẽ giám sát FastAPI application của bạn với:
- **Prometheus**: Thu thập metrics
- **Grafana**: Hiển thị dashboard
- **FastAPI Instrumentator**: Tự động thu thập HTTP metrics

## Các metrics được thu thập

### HTTP Metrics (Tự động)
- `http_requests_total`: Tổng số request
- `http_request_duration_seconds`: Thời gian xử lý request
- `http_requests_in_progress`: Số request đang xử lý

### Business Metrics (Custom)
- `user_registrations_total`: Tổng số đăng ký user
- `user_logins_total`: Tổng số đăng nhập
- `image_predictions_total`: Tổng số prediction ảnh
- `routine_completions_total`: Tổng số routine hoàn thành
- `model_inference_duration_seconds`: Thời gian inference AI model

### System Metrics (Node Exporter)
- `node_cpu_seconds_total`: CPU usage by core and mode
- `node_memory_*`: Memory usage, available, total
- `node_filesystem_*`: Disk usage, available, size
- `node_network_*`: Network I/O statistics
- `node_load*`: System load averages

### Container Metrics (cAdvisor)
- `container_cpu_usage_seconds_total`: Container CPU usage
- `container_memory_usage_bytes`: Container memory usage
- `container_fs_*`: Container filesystem metrics
- `container_network_*`: Container network metrics

## Cách chạy

### 1. Cài đặt dependencies
```bash
pip install -r requirements.txt
```

### 2. Khởi động tất cả services
```bash
docker-compose up -d
```

### 3. Truy cập các services
- **FastAPI**: http://localhost:8080
- **FastAPI Metrics**: http://localhost:8080/metrics
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin123)
- **Node Exporter**: http://localhost:9100/metrics
- **cAdvisor**: http://localhost:8081/metrics

## Cách sử dụng Grafana

### 1. Truy cập Grafana
- URL: http://localhost:3000
- Username: admin
- Password: admin123

### 2. Kiểm tra Data Source
- Vào Configuration > Data Sources
- Prometheus đã được cấu hình sẵn tại http://prometheus:9090

### 3. Xem Dashboard
- Dashboard "FastAPI Monitoring Dashboard" đã được tạo sẵn
- Hoặc tạo dashboard mới với các metrics có sẵn

## Prometheus Queries hữu ích

### HTTP Metrics
```promql
# Request rate per second
rate(http_requests_total[5m])

# Average response time
rate(http_request_duration_seconds_sum[5m]) / rate(http_request_duration_seconds_count[5m])

# Error rate
rate(http_requests_total{status=~"4..|5.."}[5m])
```

### Business Metrics
```promql
# User registration rate
rate(user_registrations_total[1h])

# Daily active users (logins)
increase(user_logins_total[24h])

# Image prediction rate
rate(image_predictions_total[5m])

# Average model inference time
rate(model_inference_duration_seconds_sum[5m]) / rate(model_inference_duration_seconds_count[5m])
```

## Troubleshooting

### 1. Metrics endpoint không hoạt động
- Kiểm tra http://localhost:8080/metrics
- Đảm bảo `prometheus-fastapi-instrumentator` đã được cài đặt

### 2. Prometheus không scrape được metrics
- Kiểm tra prometheus.yml config
- Đảm bảo target `app:8080` có thể reach được

### 3. Grafana không hiển thị data
- Kiểm tra Data Source connection
- Verify Prometheus có data bằng cách truy cập http://localhost:9090

## Mở rộng

### Thêm metrics mới
1. Thêm vào `monitoring/fastapi_metrics.py`
2. Import và sử dụng trong routes
3. Tạo dashboard panel mới trong Grafana

### Thêm alerting
1. Cấu hình Alertmanager
2. Tạo alert rules trong Prometheus
3. Setup notification channels trong Grafana 