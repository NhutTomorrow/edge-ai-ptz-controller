import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Khai báo cấu hình MQTT Server công ty [cite: 43]
    MQTT_HOST: str = os.getenv("MQTT_HOST", "mqtt.abcsolutions.com.vn")
    MQTT_PORT: int = int(os.getenv("MQTT_PORT", 1883))
    MQTT_USER: str = os.getenv("MQTT_USER", "abcsolution")
    MQTT_PASS: str = os.getenv("MQTT_PASS", "CseLAbC5c6")
    MQTT_TOPIC: str = "camera/ptz"

    # Cấu hình tĩnh hệ thống camera có thể mở rộng ra file JSON hoặc .env
    CAMERA_CONFIGS: dict = {
        "cam_lab": {
            "name": "Phòng Thí Nghiệm (Subnet A)",
            "rtsp_url": "rtsp://admin:cselabc5c6@192.168.1.200:554/Streaming/Channels/102",
            "onvif_ip": "192.168.1.200", "onvif_port": 80, "user": "admin", "pass": "cselabc5c6"
        },
        "cam_canteen": {
            "name": "Nhà Ăn Công Ty (Subnet A)",
            "rtsp_url": "rtsp://admin:cselabc5c6@192.168.1.201:554/Streaming/Channels/102",
            "onvif_ip": "192.168.1.201", "onvif_port": 80, "user": "admin", "pass": "cselabc5c6"
        },
        "cam_gate": {
            "name": "Cam truoc cua cong(Subnet B)",
            "rtsp_url": "rtsp://admin:cselabc5c6@192.168.1.203:554/Streaming/Channels/102",
            "onvif_ip": "192.168.1.203", "onvif_port": 80, "user": "admin", "pass": "cselabc5c6"
        }
    }

settings = Settings()