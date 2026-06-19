import time
import cv2
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from core.camera_manager import camera_manager
#from core.ai_pipeline import ai_pipeline  # Sẵn sàng cho luồng tích hợp AI
from config.settings import settings

# Khởi tạo Router nhánh dành cho API v1
router = APIRouter(prefix="/api/v1")

# ==================== ĐỊNH NGHĨA KHUNG DỮ LIỆU ĐẦU VÀO (SCHEMAS) ====================
class PTZCommand(BaseModel):
    direction: str = Field(..., description="Hướng di chuyển: up, down, left, right, stop")
    speed: float = Field(0.4, ge=0.0, le=1.0, description="Tốc độ xoay từ 0.0 đến 1.0")

class ZoomCommand(BaseModel):
    action: str = Field(..., description="Hành động zoom số: in (phóng to), out (thu nhỏ)")


# ==================== ĐỊNH TUYẾN CÁC ENDPOINTS CHI TIẾT ====================

@router.get("/cameras")
def list_cameras():
    """Endpoint: Lấy danh sách mạng lưới camera hiện hành và trạng thái kết nối SOAP"""
    return {
        cam_id: {
            "name": cfg["name"],
            "status": camera_manager.onvif_sessions.get(cam_id, {}).get("status", "Unknown")
        } for cam_id, cfg in settings.CAMERA_CONFIGS.items()
    }


@router.post("/camera/{cam_id}/ptz")
def control_camera_ptz(cam_id: str, cmd: PTZCommand):
    """Endpoint: Tiếp nhận lệnh điều hướng HTTP từ Dashboard, chuyển tiếp tới Core xử lý phần cứng"""
    if cam_id not in settings.CAMERA_CONFIGS:
        raise HTTPException(status_code=404, detail="Không tìm thấy ID Camera trong hệ thống")

    success = camera_manager.execute_ptz(cam_id, cmd.direction, cmd.speed)
    if success:
        return {"status": "success", "message": f"Đã thực thi lệnh {cmd.direction.upper()}"}
    raise HTTPException(status_code=500, detail="Gửi lệnh điều khiển phần cứng thất bại")


@router.post("/camera/{cam_id}/zoom")
def control_camera_digital_zoom(cam_id: str, cmd: ZoomCommand):
    """Endpoint: Xử lý tăng giảm bước mức độ Zoom số trên RAM"""
    if cam_id not in settings.CAMERA_CONFIGS:
        raise HTTPException(status_code=404, detail="Không tìm thấy ID Camera trong hệ thống")

    current_zoom = camera_manager.digital_zoom_states.get(cam_id, 1.0)

    if cmd.action == "in":
        current_zoom = min(current_zoom + 0.5, 4.0)  # Giới hạn tối đa phóng đại 4x
    elif cmd.action == "out":
        current_zoom = max(current_zoom - 0.5, 1.0)  # Giới hạn tối thiểu về gốc 1x
    else:
        raise HTTPException(status_code=400, detail="Hành động zoom không hợp lệ")

    camera_manager.digital_zoom_states[cam_id] = current_zoom
    return {"status": "success", "current_zoom": current_zoom}


@router.get("/camera/{cam_id}/stream")
def stream_camera_video(cam_id: str):
    """Endpoint: Cầu nối tối ưu truyền luồng hình ảnh MJPEG từ RAM kết hợp xử lý AI"""
    if cam_id not in settings.CAMERA_CONFIGS:
        raise HTTPException(status_code=404, detail="Không tìm thấy ID ảnh luồng Camera")

    def generate_video_stream():
        while True:
            # 1. Đọc frame thô từ bộ đệm RAM không lag của CameraManager
            raw_frame = camera_manager.latest_frames.get(cam_id)
            if raw_frame is None:
                time.sleep(0.04)  # Tránh treo CPU khi chưa có luồng nhận về
                continue

            # 2. Tạo bản sao để xử lý, tránh xung đột tài nguyên giữa các luồng đọc công cộng
            working_frame = raw_frame.copy()

            # 3. ĐẨY QUA PIPELINE AI: Nhận diện vật thể/vẽ bounding box thời gian thực
#            working_frame = ai_pipeline.process_frame(working_frame)

            # 4. THUẬT TOÁN DIGITAL ZOOM: Trích xuất ma trận cắt ảnh từ tâm nếu đang bật kích hoạt kích thước zoom
            zoom_factor = camera_manager.digital_zoom_states.get(cam_id, 1.0)
            if zoom_factor > 1.0:
                h, w = working_frame.shape[:2]
                new_h, new_w = int(h / zoom_factor), int(w / zoom_factor)
                start_y = (h - new_h) // 2
                start_x = (w - new_w) // 2
                working_frame = working_frame[start_y:start_y + new_h, start_x:start_x + new_w]

            # 5. Khớp định dạng kích thước chuẩn lưới giao diện ô đa camera
            frame_resized = cv2.resize(working_frame, (640, 360))

            # 6. Nén ảnh JPEG chất lượng cao tối ưu dung lượng đường truyền mạng
            ret, buffer = cv2.imencode('.jpg', frame_resized, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
            if not ret:
                continue

            # 7. Đóng gói luồng byte nhị phân thô đẩy ra cổng HTTP mạng
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

            time.sleep(0.04)  # Duy trì tốc độ ~25 FPS mượt mà ổn định

    return StreamingResponse(generate_video_stream(), media_type="multipart/x-mixed-replace; boundary=frame")