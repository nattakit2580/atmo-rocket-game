"""ตรวจจับแขน (ไหล่ -> ปลายนิ้ว) จากกล้องด้วย MediaPipe Pose Landmarker
ทำงานใน background thread แยกจาก game loop หลัก เพื่อไม่ให้เกมกระตุก

หลักการ: ไม่สนใจว่า mediapipe เรียกแขนไหนว่า 'left'/'right' (เพราะสลับกันได้ตามการหันตัว/กลับด้านภาพ)
แต่ดูว่าคู่ไหล่-ปลายนิ้วคู่ไหนอยู่ "ฝั่งซ้าย/ฝั่งขวาของจอ" (หลัง flip กระจกแล้ว) แล้วเช็คว่ายกขึ้นหรือไม่
วิธีนี้ทำให้ยกแขนขวาจริงๆ ของผู้เล่น (ซึ่งจะอยู่ฝั่งขวาของจอแบบกระจกเงา) แปลว่า "ขวา" เสมอ
"""
import threading
import time

import cv2
import numpy as np

try:
    import mediapipe as mp
    from mediapipe.tasks.python import BaseOptions, vision
    MEDIAPIPE_OK = True
except Exception:
    MEDIAPIPE_OK = False

RAISE_THRESHOLD = 0.06  # ปลายนิ้วต้องสูงกว่าไหล่อย่างน้อยเท่านี้ (สัดส่วนของภาพ) ถึงจะนับว่า "ยก"
SMOOTHING = 0.65  # ยิ่งสูงยิ่งลื่นแต่ตอบสนองช้าลง
PREVIEW_WIDTH = 260
PREVIEW_HEIGHT = 195
PROC_WIDTH = 400  # ลดขนาดภาพก่อนส่งเข้าโมเดลเพื่อความเร็ว

ARM_PAIRS = [(11, 15, 19), (12, 16, 20)]  # (shoulder, wrist, index) x 2 ข้าง ตามชื่อภายในของ mediapipe


class CameraState:
    def __init__(self):
        self.available = False
        self.tracking = False
        self.control = 0.0
        self.left_raised = False
        self.right_raised = False
        self.frame_rgb = None  # numpy array (H, W, 3) สำหรับพรีวิว
        self.landmarks = None  # list of (x, y) normalized หรือ None
        self.error = None


class CameraController:
    def __init__(self, model_path, cam_index=0):
        self.model_path = model_path
        self.cam_index = cam_index
        self._lock = threading.Lock()
        self._state = CameraState()
        self._running = False
        self._thread = None
        self._smoothed_control = 0.0

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=2.0)

    def get_state(self):
        with self._lock:
            return self._state

    def _publish(self, **kwargs):
        with self._lock:
            for k, v in kwargs.items():
                setattr(self._state, k, v)

    def _run(self):
        if not MEDIAPIPE_OK:
            self._publish(available=False, error="mediapipe import failed")
            return

        cap = cv2.VideoCapture(self.cam_index, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap = cv2.VideoCapture(self.cam_index)
        if not cap.isOpened():
            self._publish(available=False, error="ไม่พบกล้อง")
            return

        try:
            options = vision.PoseLandmarkerOptions(
                base_options=BaseOptions(model_asset_path=self.model_path),
                running_mode=vision.RunningMode.VIDEO,
                num_poses=1,
                min_pose_detection_confidence=0.5,
                min_tracking_confidence=0.5,
            )
            landmarker = vision.PoseLandmarker.create_from_options(options)
        except Exception as exc:
            self._publish(available=False, error=f"โหลดโมเดลไม่สำเร็จ: {exc}")
            cap.release()
            return

        self._publish(available=True, error=None)
        start_time = time.monotonic()
        last_seen = time.monotonic()

        try:
            while self._running:
                ok, frame = cap.read()
                if not ok:
                    time.sleep(0.02)
                    continue

                frame = cv2.flip(frame, 1)  # โหมดกระจกเงา ให้ตรงกับความรู้สึกธรรมชาติ
                h, w = frame.shape[:2]
                scale = PROC_WIDTH / w
                small = cv2.resize(frame, (PROC_WIDTH, int(h * scale)))
                rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)

                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                ts_ms = int((time.monotonic() - start_time) * 1000)
                result = landmarker.detect_for_video(mp_image, ts_ms)

                left_raised = False
                right_raised = False
                landmarks_out = None
                tracking = False

                if result.pose_landmarks:
                    lm = result.pose_landmarks[0]
                    tracking = True
                    last_seen = time.monotonic()

                    pair_info = []
                    for shoulder_i, wrist_i, index_i in ARM_PAIRS:
                        shoulder = lm[shoulder_i]
                        tip = lm[index_i]  # ปลายนิ้วชี้ (ประมาณตำแหน่งปลายนิ้ว, ต่อจากไหล่->ข้อมือ)
                        raised = (shoulder.y - tip.y) > RAISE_THRESHOLD
                        side_x = (shoulder.x + tip.x) / 2.0
                        pair_info.append({"raised": raised, "side_x": side_x})

                    if pair_info[0]["side_x"] <= pair_info[1]["side_x"]:
                        screen_left, screen_right = pair_info[0], pair_info[1]
                    else:
                        screen_left, screen_right = pair_info[1], pair_info[0]

                    left_raised = screen_left["raised"]
                    right_raised = screen_right["raised"]

                    landmarks_out = [(p.x, p.y) for p in lm]

                if time.monotonic() - last_seen > 1.0:
                    tracking = False

                raw_signal = 0.0
                if right_raised and not left_raised:
                    raw_signal = 1.0
                elif left_raised and not right_raised:
                    raw_signal = -1.0

                self._smoothed_control = (
                    self._smoothed_control * SMOOTHING + raw_signal * (1 - SMOOTHING)
                )

                preview = cv2.resize(rgb, (PREVIEW_WIDTH, PREVIEW_HEIGHT))

                self._publish(
                    available=True,
                    tracking=tracking,
                    control=self._smoothed_control,
                    left_raised=left_raised,
                    right_raised=right_raised,
                    frame_rgb=preview,
                    landmarks=landmarks_out,
                    error=None,
                )
        finally:
            landmarker.close()
            cap.release()
