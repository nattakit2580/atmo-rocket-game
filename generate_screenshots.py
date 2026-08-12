"""สร้างภาพหน้าจอเกมสำหรับใช้ประกอบเอกสารนำเสนอ (headless, ไม่ต้องเปิดหน้าต่างจริง)"""
import os

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import numpy as np  # noqa: E402
import pygame  # noqa: E402
import cv2  # noqa: E402

import main as game_mod  # noqa: E402
from camera_control import CameraState, PREVIEW_WIDTH, PREVIEW_HEIGHT  # noqa: E402
from entities import FallingObject  # noqa: E402
from levels_data import LEVELS  # noqa: E402

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "screenshots")
os.makedirs(OUT_DIR, exist_ok=True)

g = game_mod.Game()


def make_fake_camera_frame(arm="right"):
    frame = np.full((PREVIEW_HEIGHT, PREVIEW_WIDTH, 3), (235, 230, 222), dtype=np.uint8)
    cx = PREVIEW_WIDTH // 2
    cv2.circle(frame, (cx, 46), 22, (90, 80, 70), -1)
    cv2.rectangle(frame, (cx - 26, 66), (cx + 26, 150), (90, 80, 70), -1)
    if arm == "right":
        cv2.line(frame, (cx + 22, 80), (cx + 60, 40), (90, 80, 70), 14)
        cv2.line(frame, (cx - 22, 80), (cx - 40, 120), (90, 80, 70), 14)
    else:
        cv2.line(frame, (cx - 22, 80), (cx - 60, 40), (90, 80, 70), 14)
        cv2.line(frame, (cx + 22, 80), (cx + 40, 120), (90, 80, 70), 14)
    return frame


def fake_landmarks(arm="right"):
    lm = [(0.5, 0.5)] * 33
    lm[11] = (0.40, 0.35)   # ไหล่ซ้าย (มุมมองในจอ)
    lm[13] = (0.40, 0.50)
    lm[15] = (0.40, 0.62)
    lm[19] = (0.40, 0.66)
    lm[12] = (0.60, 0.35)   # ไหล่ขวา (มุมมองในจอ)
    lm[14] = (0.60, 0.50)
    lm[16] = (0.60, 0.62)
    lm[20] = (0.60, 0.66)
    if arm == "right":
        lm[14] = (0.72, 0.20)
        lm[16] = (0.80, 0.08)
        lm[20] = (0.82, 0.04)
    else:
        lm[13] = (0.28, 0.20)
        lm[15] = (0.20, 0.08)
        lm[19] = (0.18, 0.04)
    return lm


def set_fake_camera(arm="right"):
    fake = CameraState()
    fake.available = True
    fake.tracking = True
    fake.frame_rgb = make_fake_camera_frame(arm)
    fake.landmarks = fake_landmarks(arm)
    fake.left_raised = (arm == "left")
    fake.right_raised = (arm == "right")
    fake.control = 1.0 if arm == "right" else -1.0
    g.camera.get_state = lambda: fake


def save(name):
    path = os.path.join(OUT_DIR, name)
    pygame.image.save(g.screen, path)
    print("saved", path)


# 1) เมนูหลัก
set_fake_camera("right")
g.state = game_mod.STATE_MENU
g.draw()
save("01_menu.png")

# 2) ด่าน 1 โทรโพสเฟียร์ - กำลังเล่น
g.reset_run()
g.start_level(0)
g.state = game_mod.STATE_PLAYING
g.rocket.lives = 2
g.rocket.invuln_timer = 0
g.rocket.x = game_mod.WIDTH * 0.62
g.level_elapsed = LEVELS[0]["duration"] * 0.4
objs = LEVELS[0]["objects"]
g.objects = [
    FallingObject(objs[0], game_mod.WIDTH * 0.18, 250, 160),
    FallingObject(objs[1], game_mod.WIDTH * 0.50, 360, 190),
    FallingObject(objs[2], game_mod.WIDTH * 0.30, 500, 150),
    FallingObject(objs[0], game_mod.WIDTH * 0.62, 480, 170),
]
set_fake_camera("right")
g.draw()
save("02_playing_troposphere.png")

# 3) ด่าน 4 เทอร์โมสเฟียร์ - กำลังเล่น (โชว์บรรยากาศตอนกลางคืน/อวกาศ)
g.start_level(3)
g.rocket.lives = 3
g.rocket.invuln_timer = 0
g.rocket.x = game_mod.WIDTH * 0.45
g.level_elapsed = LEVELS[3]["duration"] * 0.55
objs4 = LEVELS[3]["objects"]
g.objects = [
    FallingObject(objs4[0], game_mod.WIDTH * 0.28, 280, 200),
    FallingObject(objs4[2], game_mod.WIDTH * 0.60, 400, 180),
    FallingObject(objs4[1], game_mod.WIDTH * 0.18, 460, 210),
]
set_fake_camera("left")
g.draw()
save("03_playing_thermosphere.png")

# 4) หน้าจอสรุปความรู้ท้ายด่าน
g.level_idx = 0
g.state = game_mod.STATE_LEVEL_COMPLETE
g.draw()
save("04_level_complete.png")

# 5) หน้าจอผ่านเกม
g.state = game_mod.STATE_GAME_WIN
g.draw()
save("05_game_win.png")

g.camera.stop()
pygame.quit()
print("DONE")
