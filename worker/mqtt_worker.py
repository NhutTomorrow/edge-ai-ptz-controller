import threading
import json
import paho.mqtt.client as mqtt
from config.settings import settings
from core.camera_manager import camera_manager

# 🟢 QUAN TRỌNG: Kế thừa danh sách camera tự động từ file cấu hình tập trung
ptz_timers = {cam_id: None for cam_id in settings.CAMERA_CONFIGS}
TIMEOUT_DURATION = 0.5  # Mã an toàn tự động dừng (0.5 giây)


def auto_stop_camera(cam_id: str):
    """Hàm callback tự động gọi khi hết thời gian timeout để bảo vệ motor"""
    print(f"⏱️ [TIMEOUT] Hết {TIMEOUT_DURATION}s mã an toàn. Tự động dừng {cam_id}...")
    # Gọi trực tiếp thực thi phần cứng từ Singleton CameraManager
    camera_manager.execute_ptz(cam_id, "stop", 0.0)


def on_mqtt_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"⚡ [MQTT] Kết nối THÀNH CÔNG tới Server công ty. Đang Subscribe topic: {settings.MQTT_TOPIC}")
        client.subscribe(settings.MQTT_TOPIC)
        # Bắn tin nhắn chào sân lên hệ thống
        hello_payload = json.dumps({"gateway_status": "online", "msg": "Pi 4 MQTT Worker is ready"})
        client.publish(settings.MQTT_TOPIC, hello_payload, qos=0)
    else:
        print(f"❌ [MQTT] Kết nối THẤT BẠI. Mã phản hồi từ Server: {rc}")


def on_mqtt_message(client, userdata, msg):
    try:
        # Giải mã dữ liệu JSON nhận được từ Broker từ xa
        payload = json.loads(msg.payload.decode('utf-8'))
        cam_id = payload.get("cam_id")
        action = payload.get("action")  # up, down, left, right, stop
        speed = payload.get("speed", 0.4)

        # Kiểm tra tính hợp lệ của ID Camera dựa trên cấu hình tập trung
        if cam_id in settings.CAMERA_CONFIGS:

            # 1. Xử lý lệnh STOP chủ động từ xa
            if action == "stop":
                if ptz_timers.get(cam_id) is not None:
                    ptz_timers[cam_id].cancel()
                    ptz_timers[cam_id] = None
                print(f"📡 [RECEIVE] Nhận lệnh STOP chủ động cho: {cam_id}")
                camera_manager.execute_ptz(cam_id, "stop", 0.0)
                return

            # 2. Xử lý các lệnh điều hướng di chuyển (up, down, left, right)
            if action in ["up", "down", "left", "right"]:
                print(f"📡 [RECEIVE] Nhận lệnh MQTT: {cam_id} -> {action} (Speed: {speed})")

                # Gọi trực tiếp tầng dịch vụ phần cứng Core để ra lệnh xoay camera
                camera_manager.execute_ptz(cam_id, action, speed)

                # LOGIC MÃ AN TOÀN TIMEOUT: Hủy bộ hẹn giờ cũ nếu có
                if ptz_timers.get(cam_id) is not None:
                    ptz_timers[cam_id].cancel()

                # Kích hoạt bộ hẹn giờ mới bảo vệ thiết bị
                ptz_timers[cam_id] = threading.Timer(TIMEOUT_DURATION, auto_stop_camera, args=(cam_id,))
                ptz_timers[cam_id].start()
            else:
                print(f"⚠️ [MQTT] Mệnh lệnh 'action' không hợp lệ: {action}")
        else:
            print(f"⚠️ [MQTT] Không tìm thấy ID camera: {cam_id}")

    except Exception as e:
        print(f"❌ [MQTT LỖI] Không thể xử lý dữ liệu nhận được: {e}")


def start_mqtt_worker():
    """
    Hàm đóng gói kiến trúc mới: Cho phép main.py kích hoạt
    luồng lắng nghe MQTT chạy song song với HTTP FastAPI Server.
    """
    print("[HỆ THỐNG] Đang khởi tạo cấu hình kết nối MQTT Client...")
    client = mqtt.Client()
    client.on_connect = on_mqtt_connect
    client.on_message = on_mqtt_message

    if settings.MQTT_USER and settings.MQTT_PASS:
        client.username_pw_set(username=settings.MQTT_USER, password=settings.MQTT_PASS)

    try:
        client.connect(settings.MQTT_HOST, settings.MQTT_PORT, 60)
        # Khởi chạy luồng lặp loop_forever dưới dạng luồng ngầm (daemon) phi block
        threading.Thread(target=client.loop_forever, daemon=True).start()
        print("🟢 MQTT Asynchronous Worker đã kích hoạt chạy ngầm thành công.")
    except Exception as e:
        print(f"❌ [LỖI KHỞI CHẠY MQTT] Không thể kết nối đến Broker: {e}")