import os
import sys
import requests
import cv2
import time
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import settings
from core.camera_manager import camera_manager

def main():
    # 1. Lấy danh sách toàn bộ ID camera đang hoạt động trong hệ thống
    cam_ids = list(camera_manager.latest_frames.keys())
    if not cam_ids:
        print("[-] Lỗi: Không tìm thấy bất kỳ cấu hình camera nào trong RAM.")
        return

    print(f"[+] Tìm thấy mạng lưới gồm {len(cam_ids)} kênh camera cần xử lý: {cam_ids}")

    # =====================================================================
    # BƯỚC 1: XÁC THỰC ĐĂNG NHẬP (LÀM TRƯỚC VÒNG LẶP ĐỂ TỐI ƯU HÓA ĐƯỜNG TRUYỀN)
    # =====================================================================
    login_payload = {
        "user_name": settings.API_USERNAME,
        "password": settings.API_PASSWORD
    }

    print("\n--- BƯỚC 1: ĐANG GỬI XÁC THỰC ĐĂNG NHẬP SẢN XUẤT ---")
    try:
        login_res = requests.post(settings.URL_LOGIN, json=login_payload, timeout=10) #
        if login_res.status_code == 200:
            print("=> Xác thực THÀNH CÔNG! Token hệ thống hợp lệ. Bắt đầu quét camera...")
        else:
            print(f"[-] Xác thực thất bại từ Server công ty. Mã lỗi HTTP: {login_res.status_code}")
            return
    except Exception as e:
        print(f"[-] Không thể kết nối tới địa chỉ IP của Server Xác thực: {e}")
        return

    # =====================================================================
    # BƯỚC 2: VÒNG LẶP DUYỆT QUÁ TOÀN BỘ CAMERA ĐỂ CHỤP VÀ GỬI ẢNH
    # =====================================================================
    print("\n--- BƯỚC 2: TIẾN TRÌNH THU THẬP VÀ TRUYỀN TẢI HÌNH ẢNH ĐA KÊNH ---")

    for cam_id in cam_ids:
        print(f"\n👉 [*] ĐANG XỬ LÝ KÊNH: [{cam_id.upper()}]")
        print(f"    [*] Đang đợi nạp khung hình từ luồng RTSP vào RAM đệm (Tối đa 10s)...")

        # Cơ chế thiết lập mã an toàn Timeout 10 giây riêng biệt cho từng camera
        frame = None
        for attempt in range(1, 11):
            frame = camera_manager.latest_frames.get(cam_id)
            if frame is not None:
                print(f"    [+] Kết nối thành công! Nhận diện ma trận ảnh sau {attempt} giây.")
                break
            time.sleep(1)

        if frame is None:
            print(f"    [-] Cảnh báo: Luồng camera [{cam_id}] đứt kết nối hoặc quá hạn (Timeout). Bỏ qua.")
            continue

        # Khởi tạo đường dẫn file ảnh tạm thời độc bản theo ID của từng camera
        image_path = f"current_frame_{cam_id}.jpg"
        cv2.imwrite(image_path, frame)

        # Thiết lập cấu trúc bản tin truyền tải dữ liệu đa phần (Multipart Form-Data)
        current_time = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        upload_payload = {
            "stationcode": settings.STATION_CODE,   # Định danh mã trạm đính kèm của Edge Gateway [cite: 149]
            "status": 4,                            # Trạng thái ảnh thô chưa xử lý theo chuẩn tài liệu API [cite: 154, 157]
            "time": current_time                    # Thời điểm chụp ảnh [cite: 155]
        }

        try:
            with open(image_path, "rb") as img_file:
                files = {
                    # Đặt tên file nhị phân kèm tên cam_id để hệ thống backend phân biệt nguồn ảnh
                    "images": (f"{cam_id}.jpg", img_file, "image/jpeg") #
                }

                print(f"    [*] Đang đẩy file ảnh của [{cam_id}] lên Server quan trắc...")
                response = requests.post(settings.URL_UPLOAD, data=upload_payload, files=files, timeout=20) # [cite: 147]

                if response.status_code == 200:
                    print(f"    => Gửi ảnh [{cam_id}] THÀNH CÔNG!")
                    print(f"    => Phản hồi từ Server: {response.json()}")
                else:
                    print(f"    [-] Server từ chối ảnh của [{cam_id}]. Mã phản hồi HTTP: {response.status_code}")

        except Exception as e:
            print(f"    [-] Gặp sự cố kết nối trong quá trình truyền tải dữ liệu mạng của [{cam_id}]: {e}")
        finally:
            # Dọn dẹp tàn dư file ảnh tạm thời trên ổ đĩa của Pi sau khi xử lý xong từng camera
            if os.path.exists(image_path):
                os.remove(image_path)

    # =====================================================================
    # KẾT THÚC TOÀN BỘ TIẾN TRÌNH
    # =====================================================================
    print("\n--------------------------------------------------")
    print("[+] Hoàn thành chu kỳ quét mạng lưới camera hệ thống.")
    camera_manager.stop()
    print("[+] Toàn bộ tiến trình kết thúc mượt mà với mã thoát 0.")
    os._exit(0)

if __name__ == "__main__":
    main()