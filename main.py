"""เกมจรวดบิน 5 ชั้นบรรยากาศ - ควบคุมด้วยการยกแขนผ่านกล้อง (ไหล่ -> ปลายนิ้ว)
ยกแขนขวา -> จรวดขยับขวา, ยกแขนซ้าย -> จรวดขยับซ้าย
ถ้าไม่มีกล้อง ใช้ปุ่มลูกศรซ้าย/ขวา (หรือ A/D) แทนได้เสมอ
"""
import os
import random
import sys

import pygame

from camera_control import CameraController
from entities import Rocket, FallingObject
from levels_data import LEVELS, TOTAL_LEVELS

if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    BASE_DIR = sys._MEIPASS  # ตอนรันจาก .exe (PyInstaller onefile) ไฟล์แนบจะถูกแตกไปไว้ที่นี่
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "models", "pose_landmarker_lite.task")

WIDTH, HEIGHT = 1000, 750
HUD_HEIGHT = 110
PLAY_MARGIN = 60
FPS = 60

STATE_MENU = "menu"
STATE_LEVEL_INTRO = "level_intro"
STATE_PLAYING = "playing"
STATE_LEVEL_COMPLETE = "level_complete"
STATE_GAME_OVER = "game_over"
STATE_GAME_WIN = "game_win"

WHITE = (255, 255, 255)
BLACK = (10, 10, 12)


def find_thai_font(size, bold=False):
    candidates = ["leelawadeeui", "tahoma", "angsanaupc", "arial"]
    available = set(pygame.font.get_fonts())
    for name in candidates:
        if name in available:
            f = pygame.font.SysFont(name, size, bold=bold)
            return f
    return pygame.font.SysFont(None, size, bold=bold)


def wrap_text(text, font, max_width):
    words = text.split(" ")
    lines = []
    current = ""
    for word in words:
        candidate = (current + " " + word).strip()
        if font.size(candidate)[0] <= max_width or not current:
            if font.size(candidate)[0] <= max_width:
                current = candidate
                continue
        # candidate too wide even alone -> hard break by characters
        if font.size(word)[0] > max_width:
            if current:
                lines.append(current)
                current = ""
            chunk = ""
            for ch in word:
                if font.size(chunk + ch)[0] <= max_width:
                    chunk += ch
                else:
                    lines.append(chunk)
                    chunk = ch
            current = chunk
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("จรวดข้ามบรรยากาศ 5 ชั้น")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()

        self.font_small = find_thai_font(18)
        self.font_med = find_thai_font(26)
        self.font_big = find_thai_font(40, bold=True)
        self.font_huge = find_thai_font(56, bold=True)

        self.camera = CameraController(MODEL_PATH)
        self.camera.start()
        self.camera_enabled = True

        self.state = STATE_MENU
        self.level_idx = 0
        self.total_lives_start = 3
        self.reset_run()

        self.keyboard_axis = 0.0
        self.state_timer = 0.0
        self.flash_timer = 0.0
        self.stars_cache = {}

    # -----------------------------------------------------------------
    def reset_run(self):
        self.level_idx = 0
        play_left = PLAY_MARGIN
        play_right = WIDTH - PLAY_MARGIN
        self.rocket = Rocket(WIDTH / 2, HEIGHT - 110, play_left, play_right)
        self.rocket.lives = self.total_lives_start
        self.objects = []
        self.level_elapsed = 0.0
        self.spawn_timer = 0.5

    def start_level(self, idx):
        self.level_idx = idx
        self.objects = []
        self.level_elapsed = 0.0
        self.spawn_timer = 0.6
        self.rocket.x = WIDTH / 2
        self.rocket.invuln_timer = 1.0

    def stars_for_level(self, idx):
        if idx not in self.stars_cache:
            rng = random.Random(idx * 999 + 7)
            n = 40 + idx * 35
            pts = [
                (rng.uniform(0, WIDTH), rng.uniform(HUD_HEIGHT, HEIGHT), rng.uniform(1, 2.6))
                for _ in range(n)
            ]
            self.stars_cache[idx] = pts
        return self.stars_cache[idx]

    # -----------------------------------------------------------------
    def get_move_control(self):
        cam_state = self.camera.get_state()
        cam_signal = cam_state.control if (self.camera_enabled and cam_state.available) else 0.0
        if abs(cam_signal) > 0.12:
            return cam_signal, cam_state
        return self.keyboard_axis, cam_state

    def handle_common_keys(self, event):
        if event.key == pygame.K_ESCAPE:
            self.quit()
        elif event.key == pygame.K_c:
            self.camera_enabled = not self.camera_enabled

    # -----------------------------------------------------------------
    def update(self, dt):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.quit()
            elif event.type == pygame.KEYDOWN:
                self.handle_common_keys(event)
                if event.key in (pygame.K_LEFT, pygame.K_a):
                    self.keyboard_axis = -1.0
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    self.keyboard_axis = 1.0
                elif event.key in (pygame.K_SPACE, pygame.K_RETURN):
                    self.advance_state()
            elif event.type == pygame.KEYUP:
                if event.key in (pygame.K_LEFT, pygame.K_a) and self.keyboard_axis < 0:
                    self.keyboard_axis = 0.0
                elif event.key in (pygame.K_RIGHT, pygame.K_d) and self.keyboard_axis > 0:
                    self.keyboard_axis = 0.0

        self.state_timer += dt
        if self.flash_timer > 0:
            self.flash_timer -= dt

        if self.state == STATE_PLAYING:
            self.update_playing(dt)

    def advance_state(self):
        if self.state == STATE_MENU:
            self.reset_run()
            self.start_level(0)
            self.state = STATE_LEVEL_INTRO
            self.state_timer = 0.0
        elif self.state == STATE_LEVEL_INTRO:
            self.state = STATE_PLAYING
            self.state_timer = 0.0
        elif self.state == STATE_LEVEL_COMPLETE:
            if self.level_idx + 1 < TOTAL_LEVELS:
                self.start_level(self.level_idx + 1)
                self.state = STATE_LEVEL_INTRO
            else:
                self.state = STATE_GAME_WIN
            self.state_timer = 0.0
        elif self.state == STATE_GAME_OVER:
            self.reset_run()
            self.start_level(0)
            self.state = STATE_LEVEL_INTRO
            self.state_timer = 0.0
        elif self.state == STATE_GAME_WIN:
            self.state = STATE_MENU
            self.state_timer = 0.0

    def update_playing(self, dt):
        level = LEVELS[self.level_idx]
        control, _ = self.get_move_control()
        self.rocket.update(dt, control)

        self.level_elapsed += dt
        progress = min(1.0, self.level_elapsed / level["duration"])

        self.spawn_timer -= dt
        if self.spawn_timer <= 0:
            lo, hi = level["spawn_interval"]
            shrink = 1.0 - 0.35 * progress
            self.spawn_timer = random.uniform(lo, hi) * shrink
            obj_def = random.choice(level["objects"])
            x = random.uniform(PLAY_MARGIN + 30, WIDTH - PLAY_MARGIN - 30)
            slo, shi = level["fall_speed"]
            speed = random.uniform(slo, shi) * (1.0 + 0.4 * progress)
            self.objects.append(FallingObject(obj_def, x, HUD_HEIGHT - 20, speed))

        for obj in self.objects:
            obj.update(dt)

        remaining = []
        for obj in self.objects:
            if obj.off_screen(HEIGHT):
                continue
            if self.rocket.rect.colliderect(obj.rect):
                if self.rocket.hit():
                    self.flash_timer = 0.25
                continue
            remaining.append(obj)
        self.objects = remaining

        if self.rocket.lives <= 0:
            self.state = STATE_GAME_OVER
            self.state_timer = 0.0
            return

        if self.level_elapsed >= level["duration"]:
            self.state = STATE_LEVEL_COMPLETE
            self.state_timer = 0.0

    # -----------------------------------------------------------------
    def draw_sky(self, level):
        top = level["sky_top"]
        bottom = level["sky_bottom"]
        h = HEIGHT - HUD_HEIGHT
        for y in range(h):
            t = y / h
            color = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
            pygame.draw.line(self.screen, color, (0, HUD_HEIGHT + y), (WIDTH, HUD_HEIGHT + y))

        if level["index"] >= 3:
            for x, y, r in self.stars_for_level(level["index"]):
                pygame.draw.circle(self.screen, (255, 255, 255), (int(x), int(y)), max(1, int(r)))

    def draw_hud(self, level):
        pygame.draw.rect(self.screen, (18, 18, 26), (0, 0, WIDTH, HUD_HEIGHT))
        title = f"ด่าน {level['index']}/{TOTAL_LEVELS}  {level['name_th']} ({level['name_en']})"
        self.screen.blit(self.font_med.render(title, True, WHITE), (20, 12))

        for i in range(self.total_lives_start):
            color = (230, 60, 70) if i < self.rocket.lives else (70, 70, 78)
            cx = 20 + i * 34
            self.draw_heart(cx, 48, color)

        progress = min(1.0, self.level_elapsed / level["duration"])
        bar_x, bar_y, bar_w, bar_h = 20, 78, 400, 16
        pygame.draw.rect(self.screen, (60, 60, 70), (bar_x, bar_y, bar_w, bar_h), border_radius=6)
        pygame.draw.rect(self.screen, (90, 200, 140), (bar_x, bar_y, int(bar_w * progress), bar_h), border_radius=6)

        alt_lo, alt_hi = level["altitude_range_km"]
        alt_now = alt_lo + (alt_hi - alt_lo) * progress
        alt_text = f"ความสูง: {alt_now:,.1f} กม."
        self.screen.blit(self.font_small.render(alt_text, True, WHITE), (bar_x + bar_w + 14, bar_y - 2))

        self.draw_camera_panel()

    def draw_heart(self, cx, cy, color):
        r = 8
        pygame.draw.circle(self.screen, color, (cx - r + 2, cy), r)
        pygame.draw.circle(self.screen, color, (cx + r - 2, cy), r)
        pygame.draw.polygon(self.screen, color, [
            (cx - 2 * r + 2, cy), (cx + 2 * r - 2, cy), (cx, cy + 2 * r),
        ])

    def draw_camera_panel(self):
        panel_w, panel_h = 260, 195
        px, py = WIDTH - panel_w - 16, 10
        cam_state = self.camera.get_state()

        pygame.draw.rect(self.screen, (0, 0, 0), (px - 4, py - 4, panel_w + 8, panel_h + 8), border_radius=8)

        if cam_state.available and cam_state.frame_rgb is not None:
            surf = pygame.image.frombuffer(
                cam_state.frame_rgb.tobytes(), (cam_state.frame_rgb.shape[1], cam_state.frame_rgb.shape[0]), "RGB"
            )
            if surf.get_size() != (panel_w, panel_h):
                surf = pygame.transform.smoothscale(surf, (panel_w, panel_h))
            self.screen.blit(surf, (px, py))

            if cam_state.landmarks:
                self.draw_skeleton(cam_state.landmarks, px, py, panel_w, panel_h, cam_state)

            status = "ตรวจจับได้" if cam_state.tracking else "ไม่เห็นตัวคุณ"
            status_color = (110, 230, 140) if cam_state.tracking else (230, 190, 90)
        else:
            self.screen.fill((40, 40, 46), (px, py, panel_w, panel_h))
            msg = self.font_small.render("ไม่พบกล้อง", True, (230, 120, 120))
            self.screen.blit(msg, msg.get_rect(center=(px + panel_w / 2, py + panel_h / 2 - 12)))
            status = "ใช้ปุ่มลูกศร ซ้าย/ขวา แทน"
            status_color = (230, 190, 90)

        cam_label = "กล้อง: เปิด" if self.camera_enabled else "กล้อง: ปิด (กด C)"
        self.screen.blit(self.font_small.render(cam_label, True, WHITE), (px, py + panel_h + 6))
        self.screen.blit(self.font_small.render(status, True, status_color), (px, py + panel_h + 26))

        control, _ = self.get_move_control()
        arrow_y = py + panel_h + 6
        left_col = (110, 230, 140) if control < -0.12 else (90, 90, 96)
        right_col = (110, 230, 140) if control > 0.12 else (90, 90, 96)
        pygame.draw.polygon(self.screen, left_col, [(px + panel_w - 44, arrow_y + 8), (px + panel_w - 30, arrow_y), (px + panel_w - 30, arrow_y + 16)])
        pygame.draw.polygon(self.screen, right_col, [(px + panel_w - 8, arrow_y + 8), (px + panel_w - 22, arrow_y), (px + panel_w - 22, arrow_y + 16)])

    def draw_skeleton(self, landmarks, px, py, panel_w, panel_h, cam_state):
        def to_screen(idx):
            x, y = landmarks[idx]
            return (px + x * panel_w, py + y * panel_h)

        # เดายศฝั่งซ้าย/ขวาของจอด้วยตำแหน่งไหล่ ด้วยหลักการเดียวกับ camera_control.py
        pair_a = (11, 13, 15, 19)  # (shoulder, elbow, wrist, index)
        pair_b = (12, 14, 16, 20)
        if landmarks[pair_a[0]][0] <= landmarks[pair_b[0]][0]:
            screen_left_pts, screen_right_pts = pair_a, pair_b
        else:
            screen_left_pts, screen_right_pts = pair_b, pair_a

        for pts_idx, raised in ((screen_left_pts, cam_state.left_raised), (screen_right_pts, cam_state.right_raised)):
            color = (255, 210, 60) if raised else (140, 200, 255)
            pts = [to_screen(i) for i in pts_idx]
            pygame.draw.lines(self.screen, color, False, pts, 3)
            for p in pts:
                pygame.draw.circle(self.screen, color, (int(p[0]), int(p[1])), 3)

        shoulder_line = [to_screen(11), to_screen(12)]
        pygame.draw.lines(self.screen, (200, 200, 210), False, shoulder_line, 2)

    # -----------------------------------------------------------------
    def draw_playing(self):
        level = LEVELS[self.level_idx]
        self.draw_sky(level)
        for obj in self.objects:
            obj.draw(self.screen, self.font_small)
        self.rocket.draw(self.screen)
        self.draw_hud(level)

        if self.flash_timer > 0:
            flash = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            alpha = int(150 * (self.flash_timer / 0.25))
            flash.fill((255, 40, 40, alpha))
            self.screen.blit(flash, (0, 0))

    def draw_centered_panel(self, lines, title=None, title_color=WHITE, hint="กด SPACE เพื่อไปต่อ"):
        self.screen.fill(BLACK)
        y = 90
        if title:
            t = self.font_huge.render(title, True, title_color)
            self.screen.blit(t, t.get_rect(center=(WIDTH / 2, y)))
            y += 70
        for line in lines:
            surf = self.font_med.render(line, True, WHITE)
            self.screen.blit(surf, surf.get_rect(center=(WIDTH / 2, y)))
            y += 38
        hint_surf = self.font_small.render(hint, True, (170, 200, 255))
        self.screen.blit(hint_surf, hint_surf.get_rect(center=(WIDTH / 2, HEIGHT - 50)))

    def draw_menu(self):
        self.screen.fill(BLACK)
        title = self.font_huge.render("จรวดข้ามบรรยากาศ 5 ชั้น", True, WHITE)
        self.screen.blit(title, title.get_rect(center=(WIDTH / 2, 220)))
        subtitle_lines = [
            "ยกแขนขวา (ไหล่ถึงปลายนิ้ว) เพื่อขยับจรวดไปทางขวา",
            "ยกแขนซ้าย เพื่อขยับจรวดไปทางซ้าย",
            "หลบสิ่งของที่ตกลงมาให้ผ่านทั้ง 5 ชั้นบรรยากาศ",
            "(ถ้าไม่มีกล้อง ใช้ปุ่มลูกศรซ้าย/ขวาแทนได้)",
        ]
        y = 320
        for line in subtitle_lines:
            surf = self.font_med.render(line, True, (200, 210, 230))
            self.screen.blit(surf, surf.get_rect(center=(WIDTH / 2, y)))
            y += 36
        hint = self.font_small.render("กด SPACE เพื่อเริ่มเกม  |  C = เปิด/ปิดกล้อง  |  ESC = ออก", True, (170, 200, 255))
        self.screen.blit(hint, hint.get_rect(center=(WIDTH / 2, HEIGHT - 60)))
        self.draw_camera_status_only()

    def draw_camera_status_only(self):
        cam_state = self.camera.get_state()
        if cam_state.available:
            msg = "ตรวจพบกล้องแล้ว" if cam_state.tracking else "เปิดกล้องอยู่ - ลองยืนให้เห็นครึ่งตัวบน"
            color = (110, 230, 140) if cam_state.tracking else (230, 190, 90)
        else:
            msg = "ไม่พบกล้อง - จะใช้ปุ่มลูกศรแทน"
            color = (230, 120, 120)
        surf = self.font_small.render(msg, True, color)
        self.screen.blit(surf, surf.get_rect(center=(WIDTH / 2, HEIGHT - 30)))

    def draw_level_intro(self):
        level = LEVELS[self.level_idx]
        lines = [f"ชั้น {level['name_th']} ({level['name_en']})"]
        self.draw_centered_panel(lines, title=f"ด่านที่ {level['index']}", hint="กด SPACE เพื่อเริ่มหลบ!")

    def draw_level_complete(self):
        level = LEVELS[self.level_idx]
        self.screen.fill(BLACK)
        title = self.font_big.render(f"จบด่าน {level['index']}: {level['name_th']}", True, (110, 230, 140))
        self.screen.blit(title, title.get_rect(center=(WIDTH / 2, 50)))

        y = 100
        for line in wrap_text(level["facts_intro"], self.font_med, WIDTH - 120):
            surf = self.font_med.render(line, True, WHITE)
            self.screen.blit(surf, surf.get_rect(center=(WIDTH / 2, y)))
            y += 32

        y += 20
        for obj in level["objects"]:
            header = f"• {obj['label']}"
            surf = self.font_med.render(header, True, (255, 210, 120))
            self.screen.blit(surf, (80, y))
            y += 30
            for line in wrap_text(obj["fact"], self.font_small, WIDTH - 180):
                surf2 = self.font_small.render(line, True, (210, 210, 220))
                self.screen.blit(surf2, (100, y))
                y += 24
            y += 6

        hint = "กด SPACE เพื่อไปด่านต่อไป" if self.level_idx + 1 < TOTAL_LEVELS else "กด SPACE เพื่อดูผลสรุป"
        hint_surf = self.font_small.render(hint, True, (170, 200, 255))
        self.screen.blit(hint_surf, hint_surf.get_rect(center=(WIDTH / 2, HEIGHT - 24)))

    def draw_game_over(self):
        lines = [
            f"ไปได้ถึงด่าน {LEVELS[self.level_idx]['index']}: {LEVELS[self.level_idx]['name_th']}",
            "ลองใหม่อีกครั้งนะ!",
        ]
        self.draw_centered_panel(lines, title="เกมโอเวอร์", title_color=(230, 90, 90), hint="กด SPACE เพื่อเริ่มใหม่")

    def draw_game_win(self):
        lines = [
            "คุณพาจรวดผ่านบรรยากาศทั้ง 5 ชั้นสำเร็จ!",
            "โทรโพสเฟียร์ - สตราโทสเฟียร์ - มีโซสเฟียร์ - เทอร์โมสเฟียร์ - เอกโซสเฟียร์",
            "ยินดีด้วย นักบินอวกาศ!",
        ]
        self.draw_centered_panel(lines, title="ภารกิจสำเร็จ!", title_color=(255, 210, 120), hint="กด SPACE เพื่อกลับเมนู")

    # -----------------------------------------------------------------
    def draw(self):
        if self.state == STATE_MENU:
            self.draw_menu()
        elif self.state == STATE_LEVEL_INTRO:
            self.draw_level_intro()
        elif self.state == STATE_PLAYING:
            self.draw_playing()
        elif self.state == STATE_LEVEL_COMPLETE:
            self.draw_level_complete()
        elif self.state == STATE_GAME_OVER:
            self.draw_game_over()
        elif self.state == STATE_GAME_WIN:
            self.draw_game_win()
        pygame.display.flip()

    def quit(self):
        self.camera.stop()
        pygame.quit()
        sys.exit(0)

    def run(self):
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            dt = min(dt, 1 / 20)
            self.update(dt)
            self.draw()


if __name__ == "__main__":
    Game().run()
