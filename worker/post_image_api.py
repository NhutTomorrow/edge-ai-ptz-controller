import os
import sys
import requests
import cv2
import time  # BẮT BUỘC IMPORT THÊM THƯ VIỆN TIME
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import settings
from core.camera_manager import camera_manager

def main():
    image_path = "current_frame.jpg"

    cam_ids = list(camera_manager.latest_frames.keys())
    if not cam_ids:
        print("[-] Lỗi: Không tìm thấy bất kỳ cấu hình camera nào.")
        return

    target_cam_id = "cam_lab" # Lấy camera 'cam_lab'

    # =====================================================================
    # SỬA ĐỔI: CƠ CHẾ CHỜ CAMERA KẾT NỐI VÀ NẠP FRAME VÀO RAM (TỐI ĐA 10 GIÂY)
    # =====================================================================
    print(f"[*] Đang kết nối tới luồng RTSP của [{target_cam_id}] qua mạng...")
    print("[*] Vui lòng đợi cấu hình và nạp khung hình vào RAM đệm (Tối đa 10s)...")

    frame = None
    for attempt in range(1, 11):
        frame = camera_manager.latest_frames[target_cam_id]
        if frame is not None:
            print(f"[+] Kết nối thành công! Lấy được frame sau {attempt} giây.")
            break
        time.sleep(1) # Nghỉ 1 giây rồi kiểm tra lại RAM

    if frame is None:
        print(f"\n[-] Cảnh báo: Luồng camera [{target_cam_id}] kết nối quá hạn (Timeout).")
      #  print("    Vui lòng kiểm tra lại thiết bị camera thực tế hoặc đường truyền Tailscale.")
        return
    # =====================================================================

    # Ghi ma trận ảnh từ RAM đệm thành file ảnh vật lý tạm thời
    cv2.imwrite(image_path, frame)

    # 2. Bước 1: Xác thực Login
    login_payload = {
        "user_name": settings.API_USERNAME,
        "password": settings.API_PASSWORD
    }

    print("\n--- BƯỚC 1: ĐANG GỬI XÁC THỰC ĐĂNG NHẬP SANG LAPTOP ---")
    try:
        login_res = requests.post(settings.URL_LOGIN, json=login_payload, timeout=10)
        if login_res.status_code == 200:
            print("=> Xác thực THÀNH CÔNG! Token hợp lệ.")
        else:
            print(f"[-] Xác thực thất bại từ Mock Server. Mã lỗi HTTP: {login_res.status_code}")
            return
    except Exception as e:
        print(f"[-] Không thể kết nối tới địa chỉ IP của Server: {e}")
        return

    # 3. Bước 2: Truyền hình ảnh qua Form-Data
    current_time = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    upload_payload = {
        "stationcode": settings.STATION_CODE,
        "status": 4,
        "time": current_time
    }

    print("--- BƯỚC 2: ĐANG TRUYỀN FILE ẢNH ---")
    try:
        with open(image_path, "rb") as img_file:
            files = {
                "images": (image_path, img_file, "image/jpeg")
            }

            response = requests.post(settings.URL_UPLOAD, data=upload_payload, files=files, timeout=20)

            if response.status_code == 200:
                print("=> Gửi ảnh THÀNH CÔNG qua mạng  về Server!")
                print(f"=> Phản hồi từ Server: {response.json()}")
            else:
                print(f"[-] Gửi ảnh thất bại. Mã phản hồi từ Server: {response.status_code}")

    except Exception as e:
        print(f"[-] Gặp sự cố kết nối trong quá trình truyền tải dữ liệu mạng: {e}")
    finally:
        if os.path.exists(image_path):
            os.remove(image_path)
        camera_manager.stop()
        print("[+] Tiến trình kết thúc mượt mà với mã thoát 0.")
        os._exit(0)

if __name__ == "__main__":
    main()
