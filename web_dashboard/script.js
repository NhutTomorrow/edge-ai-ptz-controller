const BASE_URL = `${window.location.origin}/api/v1`;
let currentCameraId = "cam_lab"; // Mặc định ban đầu chọn điều khiển cam_lab
let currentZoom = 1;

// ==================== HÀM XỬ LÝ CHUYỂN ĐỔI CAMERA TRÊN GIAO DIỆN ====================
function selectCamera(camId) {
    currentCameraId = camId;

    // 1. Gỡ bỏ trạng thái hoạt động (active) và tắt chấm đỏ của tất cả các ô camera
    document.querySelectorAll('.camera-card').forEach(card => {
        card.classList.remove('active');
        const titleEl = card.querySelector('.camera-title');
        if (titleEl) {
            titleEl.innerText = titleEl.innerText.replace('🔴', '⚪');
        }
    });

    // 2. Kích hoạt viền sáng Neon và bật chấm đỏ cho ô camera vừa được click
    const activeCard = document.getElementById(`card-${camId}`);
    if (activeCard) {
        activeCard.classList.add('active');
        const titleEl = activeCard.querySelector('.camera-title');
        if (titleEl) {
            titleEl.innerText = titleEl.innerText.replace('⚪', '🔴');
        }
    }

    // 3. Định danh lại tên camera hiển thị trên bảng điều khiển bên phải
    const cameraNames = {
        "cam_lab": "PHÒNG THÍ NGHIỆM",
        "cam_gate": "CỔNG TRƯỚC",
        "cam_canteen": "NHÀ ĂN CÔNG TY"
    };

    document.getElementById('currentTargetCam').innerText = `Đang chọn: ${cameraNames[camId]}`;
    updateLog(`Đã chuyển sang kênh điều khiển: ${cameraNames[camId]}`);
}

// ==================== HÀM GỬI LỆNH ĐIỀU HƯỚNG PTZ PHẦN CỨNG ====================
async function sendPtzCommand(direction) {
    // Đường dẫn API động thay đổi theo ID camera đang được lựa chọn
    const url = `${BASE_URL}/camera/${currentCameraId}/ptz`;
    updateLog(`Đang gửi lệnh xoay: ${direction.toUpperCase()}...`);

    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            // Cấu trúc Body JSON đã sửa lại để khớp chuẩn với Pydantic PTZCommand của main.py
            body: JSON.stringify({
                direction: direction,
                speed: 0.5
            })
        });

        if (response.ok) {
            updateLog(`Thành công: Đã thực hiện lệnh ${direction.toUpperCase()}`);
        } else {
            updateLog(`Lỗi: Server phản hồi mã lỗi ${response.status}`);
        }
    } catch (error) {
        updateLog("Lỗi: Không thể kết nối tới Edge Gateway trên Pi.");
    }
}

// ==================== HÀM XỬ LÝ TĂNG GIẢM ZOOM TẠM THỜI ===================
// Hàm xử lý tăng giảm Zoom số đồng bộ với Backend mới
async function sendZoomCommand(isZoomIn) {
    const action = isZoomIn ? "in" : "out";
    // Gọi trực tiếp đến Endpoint Zoom động của Camera đang được chọn
    const url = `${BASE_URL}/camera/${currentCameraId}/zoom`;

    updateLog(`Đang gửi yêu cầu Zoom số: ${action.toUpperCase()}...`);

    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: action })
        });

        if (response.ok) {
            const data = await response.json();
            updateLog(`Thành công: Độ phóng đại hiện tại đạt ${data.current_zoom}x`);
        } else {
            updateLog(`Lỗi: Không thể thực thi thao tác Zoom số.`);
        }
    } catch (error) {
        updateLog("Lỗi: Mất kết nối tới hệ thống Edge Gateway.");
    }
}
// ==================== HÀM TRỢ LÝ CẬP NHẬT STATUS BAR ====================
function updateLog(text) {
    document.getElementById('logBar').innerText = `Trạng thái: ${text}`;
}