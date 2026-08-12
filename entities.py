"""จรวดผู้เล่น, ของที่ตกลงมา และฟังก์ชันวาดรูปทรงต่างๆ (วาดด้วย pygame primitives ล้วน ไม่ใช้รูปภาพภายนอก)"""
import math
import random

import pygame

# ---------------------------------------------------------------------------
# จรวดผู้เล่น
# ---------------------------------------------------------------------------


class Rocket:
    def __init__(self, x, y, min_x, max_x):
        self.x = x
        self.y = y
        self.width = 46
        self.height = 86
        self.min_x = min_x
        self.max_x = max_x
        self.speed = 420.0  # px/s เมื่อควบคุมเต็มที่ (control = +-1)
        self.lives = 3
        self.invuln_timer = 0.0
        self.flame_phase = 0.0

    @property
    def rect(self):
        # กล่องชนกันเล็กกว่ารูปวาดจริงเล็กน้อยให้เกมเล่นสนุกขึ้น (ไม่หงุดหงิดง่ายเกินไป)
        w = self.width * 0.55
        h = self.height * 0.7
        return pygame.Rect(self.x - w / 2, self.y - h / 2, w, h)

    def update(self, dt, control):
        control = max(-1.0, min(1.0, control))
        self.x += control * self.speed * dt
        self.x = max(self.min_x, min(self.max_x, self.x))
        self.flame_phase += dt * 14.0
        if self.invuln_timer > 0:
            self.invuln_timer = max(0.0, self.invuln_timer - dt)

    def hit(self):
        if self.invuln_timer > 0:
            return False
        self.lives -= 1
        self.invuln_timer = 1.6
        return True

    def draw(self, surface):
        if self.invuln_timer > 0 and int(self.invuln_timer * 12) % 2 == 0:
            return  # กระพริบตอนอมตะชั่วคราว
        cx, cy = self.x, self.y
        w, h = self.width, self.height

        flame_len = 14 + 6 * math.sin(self.flame_phase)
        flame_pts = [
            (cx - w * 0.22, cy + h * 0.42),
            (cx + w * 0.22, cy + h * 0.42),
            (cx, cy + h * 0.42 + flame_len),
        ]
        pygame.draw.polygon(surface, (255, 170, 60), flame_pts)
        pygame.draw.polygon(surface, (255, 230, 140), [
            (cx - w * 0.10, cy + h * 0.42),
            (cx + w * 0.10, cy + h * 0.42),
            (cx, cy + h * 0.42 + flame_len * 0.55),
        ])

        body_pts = [
            (cx, cy - h * 0.5),
            (cx + w * 0.32, cy - h * 0.05),
            (cx + w * 0.32, cy + h * 0.42),
            (cx - w * 0.32, cy + h * 0.42),
            (cx - w * 0.32, cy - h * 0.05),
        ]
        pygame.draw.polygon(surface, (235, 240, 245), body_pts)
        pygame.draw.polygon(surface, (170, 60, 60), [
            (cx - w * 0.32, cy + h * 0.20),
            (cx - w * 0.55, cy + h * 0.44),
            (cx - w * 0.32, cy + h * 0.40),
        ])
        pygame.draw.polygon(surface, (170, 60, 60), [
            (cx + w * 0.32, cy + h * 0.20),
            (cx + w * 0.55, cy + h * 0.44),
            (cx + w * 0.32, cy + h * 0.40),
        ])
        pygame.draw.circle(surface, (110, 180, 230), (int(cx), int(cy - h * 0.12)), int(w * 0.16))
        pygame.draw.polygon(surface, (30, 30, 35), body_pts, width=2)


# ---------------------------------------------------------------------------
# ของที่ตกลงมา
# ---------------------------------------------------------------------------


class FallingObject:
    def __init__(self, obj_def, x, y, speed):
        self.obj_def = obj_def
        self.x = x
        self.y = y
        self.speed = speed
        self.size = obj_def["size"]
        self.phase = random.uniform(0, math.tau)

    def update(self, dt):
        self.y += self.speed * dt
        self.phase += dt * 3.0

    @property
    def rect(self):
        s = self.size * 0.75
        return pygame.Rect(self.x - s / 2, self.y - s / 2, s, s)

    def off_screen(self, height):
        return self.y - self.size > height

    def draw(self, surface, font):
        renderer = SHAPE_RENDERERS.get(self.obj_def["shape"], draw_cloud)
        renderer(surface, self.x, self.y, self.size, self.obj_def["color"], self.phase)

        label = self.obj_def["label"]
        text_surf = font.render(label, True, (20, 20, 25))
        bg_rect = text_surf.get_rect(center=(self.x, self.y + self.size * 0.62 + 10))
        bg = pygame.Surface((bg_rect.width + 8, bg_rect.height + 4), pygame.SRCALPHA)
        bg.fill((255, 255, 255, 170))
        surface.blit(bg, (bg_rect.x - 4, bg_rect.y - 2))
        surface.blit(text_surf, bg_rect)


# ---------------------------------------------------------------------------
# ฟังก์ชันวาดรูปทรงแต่ละชนิด (surface, cx, cy, size, color, phase)
# ---------------------------------------------------------------------------


def draw_cloud(surface, cx, cy, size, color, phase):
    r = size * 0.28
    offsets = [(-0.55, 0.1), (-0.15, -0.15), (0.25, -0.1), (0.55, 0.12), (0.0, 0.22)]
    for ox, oy in offsets:
        pygame.draw.circle(surface, color, (int(cx + ox * size), int(cy + oy * size)), int(r))
    pygame.draw.ellipse(surface, color, (cx - size * 0.6, cy - size * 0.05, size * 1.2, size * 0.4))


def draw_plane(surface, cx, cy, size, color, phase):
    pygame.draw.polygon(surface, color, [
        (cx, cy - size * 0.5), (cx + size * 0.08, cy + size * 0.3), (cx - size * 0.08, cy + size * 0.3),
    ])
    pygame.draw.polygon(surface, color, [
        (cx - size * 0.55, cy + size * 0.15), (cx + size * 0.55, cy + size * 0.15),
        (cx, cy - size * 0.05),
    ])
    pygame.draw.polygon(surface, (150, 60, 60), [
        (cx - size * 0.18, cy + size * 0.28), (cx + size * 0.18, cy + size * 0.28),
        (cx, cy + size * 0.45),
    ])


def draw_bird(surface, cx, cy, size, color, phase):
    flap = math.sin(phase * 4.0) * size * 0.18
    pygame.draw.arc(surface, color, (cx - size * 0.5, cy - flap - size * 0.15, size * 0.5, size * 0.4),
                     0.2, math.pi - 0.2, 4)
    pygame.draw.arc(surface, color, (cx, cy - flap - size * 0.15, size * 0.5, size * 0.4),
                     0.2, math.pi - 0.2, 4)


def draw_balloon(surface, cx, cy, size, color, phase):
    pygame.draw.circle(surface, color, (int(cx), int(cy - size * 0.12)), int(size * 0.42))
    pygame.draw.polygon(surface, color, [
        (cx - size * 0.14, cy + size * 0.22), (cx + size * 0.14, cy + size * 0.22), (cx, cy + size * 0.38),
    ])
    pygame.draw.rect(surface, (90, 70, 50), (cx - size * 0.12, cy + size * 0.4, size * 0.24, size * 0.16))
    pygame.draw.line(surface, (90, 70, 50), (cx - size * 0.1, cy + size * 0.38), (cx - size * 0.1, cy + size * 0.4), 2)
    pygame.draw.line(surface, (90, 70, 50), (cx + size * 0.1, cy + size * 0.38), (cx + size * 0.1, cy + size * 0.4), 2)


def draw_ray(surface, cx, cy, size, color, phase):
    pts = [
        (cx - size * 0.12, cy - size * 0.5), (cx + size * 0.1, cy - size * 0.05),
        (cx - size * 0.05, cy - size * 0.05), (cx + size * 0.12, cy + size * 0.5),
        (cx - size * 0.1, cy + size * 0.05), (cx + size * 0.05, cy + size * 0.05),
    ]
    pygame.draw.polygon(surface, color, pts)
    glow = pygame.Surface((size * 1.6, size * 1.6), pygame.SRCALPHA)
    pygame.draw.circle(glow, (*color, 60), (int(size * 0.8), int(size * 0.8)), int(size * 0.7))
    surface.blit(glow, (cx - size * 0.8, cy - size * 0.8))


def draw_meteor(surface, cx, cy, size, color, phase):
    trail_len = size * 1.4
    pygame.draw.polygon(surface, (255, 235, 190), [
        (cx, cy), (cx - trail_len * 0.35, cy - trail_len * 0.85), (cx - trail_len * 0.15, cy - trail_len * 0.9),
        (cx + trail_len * 0.1, cy),
    ])
    pygame.draw.circle(surface, color, (int(cx), int(cy)), int(size * 0.22))


def draw_noctilucent(surface, cx, cy, size, color, phase):
    for i in range(3):
        yy = cy - size * 0.15 + i * size * 0.15
        points = []
        for t in range(-3, 4):
            xx = cx + t * size * 0.18
            points.append((xx, yy + math.sin(phase + t * 0.9 + i) * size * 0.06))
        if len(points) >= 2:
            pygame.draw.lines(surface, color, False, points, 5)


def draw_small_rocket(surface, cx, cy, size, color, phase):
    pygame.draw.polygon(surface, color, [
        (cx, cy - size * 0.5), (cx + size * 0.16, cy + size * 0.15), (cx - size * 0.16, cy + size * 0.15),
    ])
    pygame.draw.rect(surface, color, (cx - size * 0.16, cy + size * 0.15, size * 0.32, size * 0.28))
    pygame.draw.polygon(surface, (200, 70, 70), [
        (cx - size * 0.16, cy + size * 0.3), (cx - size * 0.3, cy + size * 0.45), (cx - size * 0.16, cy + size * 0.43),
    ])
    pygame.draw.polygon(surface, (200, 70, 70), [
        (cx + size * 0.16, cy + size * 0.3), (cx + size * 0.3, cy + size * 0.45), (cx + size * 0.16, cy + size * 0.43),
    ])
    pygame.draw.polygon(surface, (255, 170, 60), [
        (cx - size * 0.1, cy + size * 0.43), (cx + size * 0.1, cy + size * 0.43), (cx, cy + size * 0.6),
    ])


def draw_aurora(surface, cx, cy, size, color, phase):
    colors = [color, (120, 130, 255), (200, 100, 220)]
    for i, col in enumerate(colors):
        points = []
        for t in range(-4, 5):
            xx = cx + t * size * 0.16
            yy = cy + math.sin(phase * 1.3 + t * 0.6 + i * 1.4) * size * 0.22 + i * size * 0.12 - size * 0.15
            points.append((xx, yy))
        if len(points) >= 2:
            pygame.draw.lines(surface, col, False, points, 6)


def draw_satellite(surface, cx, cy, size, color, phase):
    pygame.draw.rect(surface, color, (cx - size * 0.14, cy - size * 0.2, size * 0.28, size * 0.4))
    panel_col = (70, 100, 200)
    pygame.draw.rect(surface, panel_col, (cx - size * 0.55, cy - size * 0.12, size * 0.35, size * 0.24))
    pygame.draw.rect(surface, panel_col, (cx + size * 0.2, cy - size * 0.12, size * 0.35, size * 0.24))
    pygame.draw.line(surface, (150, 150, 160), (cx - size * 0.2, cy), (cx - size * 0.55 + size * 0.35, cy), 2)
    pygame.draw.line(surface, (150, 150, 160), (cx + size * 0.2, cy), (cx + size * 0.2 + 0, cy), 2)
    pygame.draw.line(surface, (150, 150, 160), (cx, cy - size * 0.2), (cx, cy - size * 0.35), 2)


def draw_station(surface, cx, cy, size, color, phase):
    pygame.draw.rect(surface, color, (cx - size * 0.32, cy - size * 0.09, size * 0.64, size * 0.18))
    panel_col = (80, 110, 210)
    for ox in (-0.6, -0.35, 0.2, 0.45):
        pygame.draw.rect(surface, panel_col, (cx + ox * size, cy - size * 0.14, size * 0.18, size * 0.28))
    pygame.draw.rect(surface, (210, 210, 220), (cx - size * 0.08, cy - size * 0.3, size * 0.16, size * 0.6))


def draw_capsule(surface, cx, cy, size, color, phase):
    pygame.draw.polygon(surface, color, [
        (cx, cy - size * 0.5), (cx + size * 0.3, cy), (cx - size * 0.3, cy),
    ])
    pygame.draw.rect(surface, color, (cx - size * 0.3, cy, size * 0.6, size * 0.32))
    pygame.draw.polygon(surface, (200, 90, 60), [
        (cx - size * 0.3, cy + size * 0.1), (cx - size * 0.5, cy + size * 0.4), (cx - size * 0.3, cy + size * 0.32),
    ])
    pygame.draw.polygon(surface, (200, 90, 60), [
        (cx + size * 0.3, cy + size * 0.1), (cx + size * 0.5, cy + size * 0.4), (cx + size * 0.3, cy + size * 0.32),
    ])
    pygame.draw.circle(surface, (150, 200, 230), (int(cx), int(cy + size * 0.12)), int(size * 0.12))


SHAPE_RENDERERS = {
    "cloud": draw_cloud,
    "plane": draw_plane,
    "bird": draw_bird,
    "balloon": draw_balloon,
    "ray": draw_ray,
    "meteor": draw_meteor,
    "noctilucent": draw_noctilucent,
    "small_rocket": draw_small_rocket,
    "aurora": draw_aurora,
    "satellite": draw_satellite,
    "station": draw_station,
    "capsule": draw_capsule,
}
