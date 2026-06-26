# Edge AI PTZ Camera Controller & Gateway

Dự án này thuộc **Đề tài 2: Hiện thực hệ thống giám sát Camera và tích hợp giao thức điều khiển PTZ** , được nghiên cứu và phát triển trong chương trình Thực tập tốt nghiệp Học kỳ 3/2025-2026 tại **Công ty TNHH Thương mại Dịch vụ Sản xuất ABC Solutions**. 

Hệ thống đóng vai trò như một Trung tâm điều phối tại biên (Edge Gateway), giải quyết đồng thời hai bài toán cốt lõi: xử lý thu nhận/giải mã các luồng video RTSP thời gian thực không trễ  và quản lý tập trung các lệnh điều khiển quay quét/thu phóng (Pan/Tilt/Zoom) của hệ thống camera IP công nghiệp thông qua hai giao thức ONVIF SOAP và Hikvision ISAPI Fallback Driver.

---

## 🚀 Các tính năng cốt lõi

* **Quản lý luồng video đa kênh không trễ (Zero-lag RTSP Streaming):** Hiện thực kiến trúc đa luồng (Multi-threading) nạp khung hình trực tiếp từ camera HIKVision vào RAM bộ đệm. Giới hạn kích thước cache buffer kịch sàn (`BUFFERSIZE = 1`) giúp triệt tiêu hoàn toàn hiện tượng tích lũy độ trễ hình ảnh, đảm bảo luồng video truyền tải về Web Dashboard mượt mà (< 200ms).
* **Driver điều khiển phần cứng lai (Hybrid PTZ Driver):** Tích hợp sâu thư viện ONVIF SOAP để tương tác với motor quay quét. Đồng thời tích hợp cơ chế dự phòng tự động (Automatic Fallback) sang giao thức ISAPI (XML qua HTTP Digest Authentication) của hãng HIKVision trong trường hợp cổng ONVIF bị giới hạn bởi lớp mạng bảo mật doanh nghiệp.
* **Bảo vệ motor thông minh (MQTT Fail-safe Worker):** Tích hợp Worker xử lý sự kiện bất đồng bộ qua giao thức MQTT để tiếp nhận lệnh từ hệ thống quản lý tập trung của công ty. Hiện thực cơ chế hẹn giờ an toàn (`threading.Timer`), tự động phát lệnh `STOP` sau 0.5 giây nếu không nhận được tín hiệu ngắt chủ động, ngăn ngừa hiện tượng kẹt motor hoặc camera xoay vô hạn khi mất gói tin mạng.
* **Phóng đại kỹ thuật số thời gian thực (Digital Zoom Crop):** Hiện thực thuật toán trích xuất và cắt ma trận ảnh (Matrix Crop) trực tiếp từ tâm luồng đồ họa trên RAM, hỗ trợ phóng đại từ 1.0x đến 4.0x mà không gây quá tải CPU của thiết bị phần cứng nhúng (Raspberry Pi 4).
* **Kiến trúc phân lớp mở rộng (Modular Layered Architecture):** Mã nguồn được tách biệt hoàn toàn theo nguyên lý Single Responsibility. Tách riêng tầng cấu hình, tầng lõi quản lý phần cứng, tầng xử lý sự kiện MQTT và tầng API HTTP, sẵn sàng không gian để nhúng trực tiếp các mô hình học sâu (YOLO/DeepSORT) vào pipeline xử lý mà không ảnh hưởng tới luồng điều khiển motor.

---

## 🌳 Sơ đồ cấu trúc cây thư mục (Directory Tree)

Hệ thống Edge AI PTZ Camera Controller & Gateway được tái cấu trúc từ mô hình nguyên khối phẳng (Flat Monolith) sang mô hình **Kiến trúc phân lớp hướng dịch vụ (Modular Layered Architecture)**. Việc phân tách này tuân thủ nguyên lý *Single Responsibility Principle (SRP)* và *Separation of Concerns (SoC)*, giúp mã nguồn dễ bảo trì, cô lập lỗi và sẵn sàng tích hợp các mô hình học sâu (AI Inference).

```text
edge-ai-ptz-controller/
│
├── config/
│   ├── __init__.py
│   └── settings.py          # Tầng cấu hình (Configuration Layer)
│
├── core/
│   ├── __init__.py
│   ├── camera_manager.py    # Tầng dịch vụ lõi phần cứng (Core Service Layer)
│   └── ai_pipeline.py       # Tầng xử lý thị giác máy tính (AI Vision Layer)
│
├── api/
│   ├── __init__.py
│   └── routes.py            # Tầng giao tiếp HTTP API (API Delivery Layer)
│
├── workers/
│   └── mqtt_worker.py       # Tầng xử lý sự kiện ngầm (Asynchronous Worker Layer)
│
├── web_dashboard/           # Tầng giao diện người dùng (Frontend Layer)
│   ├── index.html
│   ├── style.css
│   └── script.js
│
├── .env                     # Lưu trữ biến môi trường bảo mật (Ẩn công khai)
├── main.py                  # Điểm khởi chạy trung tâm (Application Entrypoint)
└── requirements.txt         # Danh sách quản lý thư viện phụ thuộc
Hệ thống được tổ chức vận hành theo luồng dữ liệu 3 lớp tuần tự khép kín:



## 🛠️ Hướng dẫn khởi chạy hệ thống
### 1. Di chuyển vào thư mục dự án
cd ~/edge-ai-ptz-controller

### 2. Kích hoạt môi trường ảo vtenv của hệ thống
source ~/vtenv/bin/activate

### 3. Cài đặt các thư viện lõi cốt lỏi của hệ thống
pip install fastapi uvicorn paho-mqtt opencv-python onvif-zeep requests pydantic-settings

### 4. Khởi chạy máy chủ API Gateway và Worker nền MQTT
python main.py
