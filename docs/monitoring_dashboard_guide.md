# Hướng dẫn sử dụng Dashboard Monitoring với Request Count

## 🚀 Tổng quan

Dashboard mới đã được nâng cấp để **count request** thay vì chỉ xem rate. Bạn có thể theo dõi:

- ✅ **Total Request Count** - Tổng số request từ trước đến nay
- ✅ **Request Count theo thời gian** (1h, 24h)
- ✅ **Request Count by Endpoint**
- ✅ **Request Count by Status Code**
- ✅ **Business Metrics Count**

## 📊 Dashboard Features

### 1. **Request Count Overview**
```promql
# Tổng số request
sum(http_requests_total)

# Request trong 1 giờ qua
sum(increase(http_requests_total[1h]))

# Request trong 24 giờ qua
sum(increase(http_requests_total[24h]))

# Số lỗi trong 1 giờ qua
sum(increase(http_requests_total{status=~"4..|5.."}[1h]))
```

### 2. **Request Count by Endpoint**
```promql
# Count theo endpoint
sum by (handler) (http_requests_total)

# Count theo endpoint trong 5 phút
sum by (handler) (increase(http_requests_total[5m]))
```

### 3. **Request Count by Status Code**
```promql
# Count theo status code
sum by (status) (http_requests_total)

# Count theo status code trong 5 phút
sum by (status) (increase(http_requests_total[5m]))
```

### 4. **Business Metrics Count**
```promql
# Tổng đăng ký user
user_registrations_total

# Tổng đăng nhập
user_logins_total

# Tổng prediction ảnh
image_predictions_total

# Tổng hoàn thành routine
routine_completions_total
```

## 🎯 Các Panel mới

### **FastAPI Monitoring Dashboard** 
- ✅ HTTP Request Rate (giữ nguyên)
- ✅ Total Requests Per Second (giữ nguyên) 
- 🆕 **Total Request Count**
- 🆕 **Requests Last Hour**
- 🆕 **Requests Last 24 Hours**
- 🆕 **Error Count (Last Hour)**
- 🆕 **Request Count by Endpoint**
- 🆕 **Request Count by Status Code**
- ✅ HTTP Request Duration (giữ nguyên)
- 🆕 **Business Metrics Count** (4 panels)

### **Enhanced FastAPI Request Monitoring**
- 🆕 **6 Stat panels** với color coding
- 🆕 **Request Count by Endpoint** (timeseries với legend)
- 🆕 **Request Count by Status Code** (stacked với color coding)
- 🆕 **Request Count by HTTP Method**
- 🆕 **Request Distribution Pie Chart**
- 🆕 **Business Metrics** (4 stat panels)

## 📈 Cách sử dụng

### 1. **Truy cập Grafana**
```bash
http://localhost:3000
Username: admin
Password: admin123
```

### 2. **Xem Dashboards**
- **FastAPI Monitoring Dashboard** - Dashboard gốc đã nâng cấp
- **Enhanced FastAPI Request Monitoring** - Dashboard chi tiết hơn

### 3. **Theo dõi Request Count**

#### **Real-time Counting:**
- Total Request Count hiển thị tổng số request từ trước đến nay
- Requests Last Hour/24h hiển thị số request gần đây
- Error Count hiển thị số lỗi

#### **Historical Analysis:**
- Request Count by Endpoint - xem endpoint nào được gọi nhiều nhất
- Request Count by Status Code - phân tích success vs error rates
- Request Distribution Pie Chart - tỷ lệ phân bố request

#### **Business Intelligence:**
- User Registrations/Logins - theo dõi user activity
- Image Predictions - theo dõi AI usage
- Routine Completions - theo dõi app engagement

## 🔧 Queries hữu ích cho Request Count

### **Top Endpoints by Request Count**
```promql
topk(10, sum by (handler) (http_requests_total))
```

### **Request Growth Rate**
```promql
# Growth rate trong 1 giờ
(sum(increase(http_requests_total[1h])) / sum(increase(http_requests_total[1h] offset 1h))) * 100 - 100
```

### **Error Percentage**
```promql
(sum(http_requests_total{status=~"4..|5.."}) / sum(http_requests_total)) * 100
```

### **Request Count Prediction (Linear)**
```promql
predict_linear(sum(http_requests_total)[1h:], 3600)
```

## 📱 Mobile-friendly

Dashboard đã được tối ưu để hiển thị tốt trên mobile và tablet với:
- Responsive grid layout
- Color-coded stat panels
- Compact legends
- Touch-friendly controls

## 🚨 Alerting

Bạn có thể tạo alerts cho:
- Request count growth quá nhanh
- Error count tăng cao
- Endpoint specific thresholds
- Business metrics anomalies

## 🎨 Color Coding

- 🟢 **Green**: Normal/Success (2xx)
- 🔵 **Blue**: Information/Low values  
- 🟡 **Yellow**: Warning/Medium values
- 🔴 **Red**: Error/High values (4xx/5xx)

---

**Note**: Dashboard sẽ tự động refresh mỗi 5s và hiển thị data realtime từ Prometheus metrics! 