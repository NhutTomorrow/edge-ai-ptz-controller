import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from api.routes import router
from workers.mqtt_worker import start_mqtt_worker # Khởi chạy song song worker nền

app = FastAPI(title="AI-Powered HIKVision Edge Gateway")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Đăng ký các API Endpoint điều khiển
app.include_router(router)

# Gắn thư mục giao diện Web Tĩnh (Thay thế cho các hàm @app.get đọc file thủ công cũ)
app.mount("/", StaticFiles(directory="web_dashboard", html=True), name="web_dashboard")

if __name__ == "__main__":
    # Kích hoạt worker lắng nghe lệnh điều khiển MQTT của công ty [cite: 43]
    start_mqtt_worker()
    
    # Khởi chạy máy chủ HTTP API Gateway
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)