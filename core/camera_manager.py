import cv2
import time
import threading
import requests
from requests.auth import HTTPDigestAuth
from onvif import ONVIFCamera
from config.settings import settings

class CameraManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CameraManager, cls).__new__(cls)
            cls._instance.init_manager()
        return cls._instance

    def init_manager(self):
        self.configs = settings.CAMERA_CONFIGS
        self.latest_frames = {cam_id: None for cam_id in self.configs}
        self.onvif_sessions = {}
        self.digital_zoom_states = {cam_id: 1.0 for cam_id in self.configs}

        # Khởi chạy luồng nạp kết nối và thu nhận frame tự động
        threading.Thread(target=self._init_all_onvif_sessions, daemon=True).start()
        for cam_id in self.configs:
            threading.Thread(target=self._camera_frame_grabber, args=(cam_id,), daemon=True).start()

    def _camera_frame_grabber(self, cam_id: str):
        rtsp_url = self.configs[cam_id]["rtsp_url"]
        cap = cv2.VideoCapture(rtsp_url)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        while True:
            ret, frame = cap.read()
            if not ret:
                cap.open(rtsp_url)
                time.sleep(1)
                continue
            self.latest_frames[cam_id] = frame

    def _init_all_onvif_sessions(self):
        for cam_id, cfg in self.configs.items():
            self.onvif_sessions[cam_id] = {
                "ptz_service": None, "req_move": None, "req_stop": None,
                "fallback_isapi": False, "cfg": cfg, "status": "Đang kết nối..."
            }
            try:
                cam = ONVIFCamera(cfg["onvif_ip"], cfg["onvif_port"], cfg["user"], cfg["pass"])
                media = cam.create_media_service()
                profile = media.GetProfiles()[0]
                ptz = cam.create_ptz_service()

                req_move = ptz.create_type('ContinuousMove')
                req_move.ProfileToken = profile.token
                req_stop = ptz.create_type('Stop')
                req_stop.ProfileToken = profile.token

                self.onvif_sessions[cam_id].update({
                    "ptz_service": ptz, "req_move": req_move, "req_stop": req_stop, "status": "ONVIF Sẵn Sàng"
                })
            except Exception:
                self.onvif_sessions[cam_id]["fallback_isapi"] = True
                self.onvif_sessions[cam_id]["status"] = "ONVIF Giới Hạn -> Đã Bật Driver Dự Phòng ISAPI"

    def execute_ptz(self, cam_id: str, direction: str, speed: float) -> bool:
        session = self.onvif_sessions.get(cam_id)
        if not session:
            return False

        pan, tilt = 0.0, 0.0
        if direction == "up": tilt = speed
        elif direction == "down": tilt = -speed
        elif direction == "left": pan = -speed
        elif direction == "right": pan = speed

        if direction == "stop":
            if session["fallback_isapi"]:
                cfg = session["cfg"]
                url = f"http://{cfg['onvif_ip']}/ISAPI/PTZCtrl/channels/1/continuous"
                xml_payload = '<?xml version="1.0" encoding="UTF-8"?><PTZData><pan>0</pan><tilt>0</tilt></PTZData>'
                res = requests.put(url, data=xml_payload, auth=HTTPDigestAuth(cfg["user"], cfg["pass"]), headers={"Content-Type": "application/xml"}, timeout=2)
                return res.status_code in [200, 201]
            else:
                ptz, req = session["ptz_service"], session["req_stop"]
                if ptz and req:
                    req.PanTilt = True
                    ptz.Stop(req)
                    return True
            return False

        if session["fallback_isapi"]:
            cfg = session["cfg"]
            hik_pan, hik_tilt = int(pan * 100), int(tilt * 100)
            url = f"http://{cfg['onvif_ip']}/ISAPI/PTZCtrl/channels/1/continuous"
            xml_payload = f'<?xml version="1.0" encoding="UTF-8"?><PTZData><pan>{hik_pan}</pan><tilt>{hik_tilt}</tilt></PTZData>'
            res = requests.put(url, data=xml_payload, auth=HTTPDigestAuth(cfg["user"], cfg["pass"]), headers={"Content-Type": "application/xml"}, timeout=2)
            return res.status_code in [200, 201]
        else:
            ptz, req = session["ptz_service"], session["req_move"]
            if ptz and req:
                req.Velocity = {'PanTilt': {'x': float(pan), 'y': float(tilt)}}
                self.ptz.ContinuousMove(req)
                return True
        return False

camera_manager = CameraManager()