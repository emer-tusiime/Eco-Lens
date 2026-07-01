#!/usr/bin/env python3
"""
EcoLens Kiosk v2 - Raspberry Pi Touchscreen UI

Improvements over v1:
  - Virtual on-screen alphanumeric keyboard (no physical keyboard required)
  - unitId sent with every session start (enables per-kiosk admin monitoring)
  - Kiosk full detection: stops accepting after KIOSK_CAPACITY bottles
  - Auto-syncs capacity with backend so admin can remotely reset via dashboard
  - Tracks all scanned items (accepted + rejected), not just accepted
  - DISPOSE AGAIN returns to session screen instead of auto-firing camera
  - Capacity bar visible during active sessions
  - Goes straight to FULL screen on startup if already at capacity
"""
import pygame
import sys
import os
import requests
import threading
import time
import io
import math
from datetime import datetime
from PIL import Image
from picamera2 import Picamera2

# ─── CONFIG ────────────────────────────────────────────────────────────────────
BACKEND_URL       = "https://eco-lens-production.up.railway.app"
ML_SERVICE_URL    = "http://localhost:7860"  # ML runs locally on the Pi
UNIT_ID           = "7fe03643-1b25-4e8e-8b88-ee4b2cde83f0"
CAPTURE_DIR       = "/home/ecolens/captures"
BOTTLE_COUNT_FILE = "/home/ecolens/bottle_count.txt"
KIOSK_CAPACITY    = 10          # max bottles before KIOSK FULL screen
SCREEN_W          = 480
SCREEN_H          = 320
FPS               = 30

# ─── COLORS ────────────────────────────────────────────────────────────────────
BG_DARK      = (8,   18,  12)
BG_CARD      = (14,  32,  20)
GREEN_BRIGHT = (0,   230, 100)
GREEN_DIM    = (0,   140, 60)
RED_BRIGHT   = (230, 60,  60)
RED_DIM      = (140, 30,  30)
TEAL         = (0,   200, 180)
WHITE        = (240, 245, 240)
GRAY         = (80,  100, 85)
GRAY_LIGHT   = (130, 150, 135)
AMBER        = (255, 190, 0)
BLACK        = (0,   0,   0)

# ─── VIRTUAL KEYBOARD LAYOUT ──────────────────────────────────────────────────
KB_ROWS = [
    ['1','2','3','4','5','6','7','8','9','0'],
    ['Q','W','E','R','T','Y','U','I','O','P'],
    ['A','S','D','F','G','H','J','K','L','<'],   # '<' = backspace
    ['Z','X','C','V','B','N','M','CLR','OK'],
]
KB_KEY_W = 44
KB_KEY_H = 34
KB_GAP   = 2
KB_LEFT  = 10


class EcoLensKiosk:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H), pygame.FULLSCREEN)
        pygame.display.set_caption("EcoLens")
        pygame.mouse.set_visible(True)

        self.f_xl   = pygame.font.SysFont("DejaVu Sans", 30, bold=True)
        self.f_lg   = pygame.font.SysFont("DejaVu Sans", 22, bold=True)
        self.f_md   = pygame.font.SysFont("DejaVu Sans", 16)
        self.f_sm   = pygame.font.SysFont("DejaVu Sans", 13)
        self.f_xs   = pygame.font.SysFont("DejaVu Sans", 11)
        self.f_mono = pygame.font.SysFont("DejaVu Sans Mono", 20, bold=True)
        self.f_kb   = pygame.font.SysFont("DejaVu Sans", 13, bold=True)

        # Session state
        self.state          = "home"
        self.user_id_input  = ""
        self.user_code      = ""
        self.session_id     = None
        self.result_valid   = False
        self.result_label   = ""
        self.result_conf    = 0.0
        self.result_points  = 0
        self.total_points   = 0
        self.total_items    = 0    # all items scanned (accepted + rejected)
        self.accepted_items = 0    # plastic items accepted
        self.status_msg     = ""
        self.status_color   = WHITE

        # Capacity
        self.bottle_count    = self._load_bottle_count()
        self.last_full_check = 0   # epoch seconds; 0 triggers immediate check

        # Animation
        self.anim_tick = 0
        self.pulse     = 0.0
        self.pulse_dir = 1

        # Button refs (set during render, read during click handling)
        self.btn_dispose_again  = None
        self.btn_end_from_result = None
        self.btn_check_status   = None
        self.kb_rects           = {}

        os.makedirs(CAPTURE_DIR, exist_ok=True)

        self.camera = None
        self._init_camera()

        # Sync capacity from backend in case admin reset it since last run
        threading.Thread(target=self._sync_capacity_from_backend, daemon=True).start()
        threading.Thread(target=self._warmup, daemon=True).start()

        self.clock = pygame.time.Clock()

    # ─── CAPACITY ──────────────────────────────────────────────────────────────
    def _load_bottle_count(self):
        try:
            with open(BOTTLE_COUNT_FILE, 'r') as f:
                return max(0, int(f.read().strip()))
        except Exception:
            return 0

    def _save_bottle_count(self):
        try:
            with open(BOTTLE_COUNT_FILE, 'w') as f:
                f.write(str(self.bottle_count))
        except Exception as e:
            print(f"[CAPACITY] save error: {e}")

    def _sync_capacity_from_backend(self):
        """On startup: if admin reset the count via dashboard, pick up that lower value."""
        if UNIT_ID == "YOUR-UNIT-UUID-HERE":
            return
        try:
            r = requests.get(
                f"{BACKEND_URL}/api/disposal/kiosks/{UNIT_ID}/status",
                timeout=5
            )
            if r.status_code == 200:
                backend_count = r.json().get("currentBottleCount", self.bottle_count)
                if backend_count < self.bottle_count:
                    self.bottle_count = backend_count
                    self._save_bottle_count()
                    print(f"[CAPACITY] synced from backend → {self.bottle_count}")
        except Exception as e:
            print(f"[CAPACITY] startup sync error: {e}")

    def _report_capacity_to_backend(self):
        """Background: tell backend the current bottle count after each disposal."""
        if UNIT_ID == "YOUR-UNIT-UUID-HERE":
            return
        try:
            requests.patch(
                f"{BACKEND_URL}/api/disposal/kiosks/{UNIT_ID}/capacity",
                json={"bottleCount": self.bottle_count},
                timeout=5
            )
        except Exception as e:
            print(f"[CAPACITY] report error: {e}")

    def _check_if_admin_reset(self):
        """Called from full screen: ask backend if admin emptied the kiosk."""
        self.last_full_check = time.time()
        if UNIT_ID == "YOUR-UNIT-UUID-HERE":
            self.bottle_count = 0
            self._save_bottle_count()
            self.state = "home"
            self.status_msg = "Kiosk ready"
            self.status_color = GREEN_BRIGHT
            return
        try:
            r = requests.get(
                f"{BACKEND_URL}/api/disposal/kiosks/{UNIT_ID}/status",
                timeout=5
            )
            if r.status_code == 200:
                backend_count = r.json().get("currentBottleCount", self.bottle_count)
                if backend_count < self.bottle_count:
                    self.bottle_count = backend_count
                    self._save_bottle_count()
                if self.bottle_count < KIOSK_CAPACITY:
                    self.status_msg = "Kiosk emptied. Ready!"
                    self.status_color = GREEN_BRIGHT
                    self.state = "home"
        except Exception as e:
            print(f"[CAPACITY] reset check error: {e}")

    # ─── CAMERA & WARMUP ───────────────────────────────────────────────────────
    def _init_camera(self):
        try:
            self.camera = Picamera2()
            cfg = self.camera.create_still_configuration(
                main={"size": (1280, 960)},
                lores={"size": (640, 480)}
            )
            self.camera.configure(cfg)
            self.camera.start()
            time.sleep(1.5)
            print("[CAMERA] initialised")
        except Exception as e:
            print(f"[CAMERA ERROR] {e}")

    def _warmup(self):
        try:
            requests.get(f"{BACKEND_URL}/health", timeout=5)
            print("[WARMUP] backend OK")
        except Exception as e:
            print(f"[WARMUP] {e}")

    # ─── API CALLS ─────────────────────────────────────────────────────────────
    def api_start_session(self):
        self.state = "loading"
        self.status_msg = "Starting session..."
        try:
            payload = {"userCode": self.user_code}
            if UNIT_ID != "YOUR-UNIT-UUID-HERE":
                payload["unitId"] = UNIT_ID

            r = requests.post(
                f"{BACKEND_URL}/api/disposal/sessions/start",
                json=payload, timeout=8
            )
            print(f"[START] {r.status_code} {r.text[:200]}")
            data = r.json()

            if r.status_code in (200, 201):
                self.session_id     = data.get("session", {}).get("id")
                self.total_points   = 0
                self.total_items    = 0
                self.accepted_items = 0
                self.status_msg     = f"Welcome, {data.get('userName', '')}!"
                self.state          = "session"
            else:
                msg = data.get("message") or data.get("error") or f"Error {r.status_code}"
                self.status_msg   = msg
                self.status_color = RED_BRIGHT
                self.state        = "home"
        except requests.exceptions.ConnectionError:
            self.status_msg   = "Cannot reach server"
            self.status_color = RED_BRIGHT
            self.state        = "home"
        except Exception as e:
            self.status_msg   = str(e)[:40]
            self.status_color = RED_BRIGHT
            self.state        = "home"

    def api_capture_and_classify(self):
        # Guard: never accept if already full
        if self.bottle_count >= KIOSK_CAPACITY:
            self.state = "full"
            return

        self.state = "capturing"
        try:
            time.sleep(0.3)
            arr = self.camera.capture_array("main")
            img = Image.fromarray(arr)

            stamp = datetime.now().strftime("%H%M%S")
            img.save(os.path.join(CAPTURE_DIR, f"{stamp}.jpg"), format="JPEG", quality=90)

            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=90)
            buf.seek(0)

            r = requests.post(
                f"{ML_SERVICE_URL}/classify",
                files={"file": ("item.jpg", buf, "image/jpeg")},
                timeout=30
            )
            print(f"[CLASSIFY] {r.status_code} {r.text[:200]}")
            ml = r.json()
            is_plastic    = ml.get("isPlastic", False)
            classified_as = ml.get("classifiedAs", "unknown")
            confidence    = float(ml.get("confidence", 0))

            r2 = requests.post(
                f"{BACKEND_URL}/api/disposal/events",
                json={
                    "sessionId":    self.session_id,
                    "classifiedAs": classified_as,
                    "confidence":   confidence,
                    "isPlastic":    is_plastic,
                },
                timeout=10
            )
            print(f"[EVENT] {r2.status_code} {r2.text[:200]}")
            data = r2.json()

            self.result_valid  = is_plastic
            self.result_label  = classified_as
            self.result_conf   = confidence
            self.result_points = int(data.get("event", {}).get("pointsAwarded", 0))

            self.total_items += 1
            if self.result_valid:
                self.total_points   += self.result_points
                self.accepted_items += 1
                self.bottle_count   += 1
                self._save_bottle_count()
                threading.Thread(target=self._report_capacity_to_backend, daemon=True).start()

            self.state = "result"

        except requests.exceptions.ConnectionError:
            self.result_valid, self.result_label = False, "Backend unreachable"
            self.result_conf, self.result_points = 0, 0
            self.total_items += 1
            self.state = "result"
        except Exception as e:
            print(f"[CLASSIFY ERROR] {e}")
            self.result_valid, self.result_label = False, str(e)[:30]
            self.result_conf, self.result_points = 0, 0
            self.total_items += 1
            self.state = "result"

    def api_end_session(self):
        self.state = "loading"
        self.status_msg = "Ending session..."
        try:
            r = requests.post(
                f"{BACKEND_URL}/api/disposal/sessions/end",
                json={"sessionId": self.session_id}, timeout=8
            )
            print(f"[END] {r.status_code} {r.text[:200]}")
            data = r.json()
            final_pts = data.get("session", {}).get("totalPoints", self.total_points)
            self.status_msg   = f"Done! {self.accepted_items} items · {final_pts} pts earned."
            self.status_color = GREEN_BRIGHT
        except Exception as e:
            print(f"[END ERROR] {e}")
            self.status_msg   = "Session closed."
            self.status_color = GRAY_LIGHT

        self.session_id     = None
        self.user_code      = ""
        self.user_id_input  = ""
        self.total_points   = 0
        self.total_items    = 0
        self.accepted_items = 0
        # Route to full screen if kiosk is now full
        self.state = "full" if self.bottle_count >= KIOSK_CAPACITY else "home"

    # ─── DRAW HELPERS ──────────────────────────────────────────────────────────
    def draw_text(self, text, font, color, x, y, center=False, right=False):
        surf = font.render(str(text), True, color)
        rect = surf.get_rect()
        if center:
            rect.centerx = x
            rect.top = y
        elif right:
            rect.right = x
            rect.top = y
        else:
            rect.topleft = (x, y)
        self.screen.blit(surf, rect)
        return rect

    def draw_button(self, label, x, y, w, h, bg, fg=BLACK, radius=8):
        pygame.draw.rect(self.screen, bg, (x, y, w, h), border_radius=radius)
        surf = self.f_md.render(label, True, fg)
        self.screen.blit(surf, surf.get_rect(center=(x + w // 2, y + h // 2)))
        return pygame.Rect(x, y, w, h)

    def draw_scanline_bg(self):
        self.screen.fill(BG_DARK)
        for yy in range(0, SCREEN_H, 4):
            pygame.draw.line(self.screen, (0, 60, 20), (0, yy), (SCREEN_W, yy))

    def draw_header_bar(self, title, show_user=False):
        pygame.draw.rect(self.screen, BG_CARD, (0, 0, SCREEN_W, 36))
        pygame.draw.line(self.screen, GREEN_DIM, (0, 36), (SCREEN_W, 36), 1)
        pygame.draw.circle(self.screen, GREEN_BRIGHT, (14, 18), 5)
        pygame.draw.circle(self.screen, BG_DARK, (14, 18), 2)
        self.draw_text("ECOLENS", self.f_sm, GREEN_BRIGHT, 24, 12)
        self.draw_text(title, self.f_sm, GRAY_LIGHT, SCREEN_W // 2, 12, center=True)
        if show_user and self.user_code:
            self.draw_text(self.user_code, self.f_sm, TEAL, SCREEN_W - 8, 12, right=True)

    def draw_capacity_bar(self, x, y, w, h):
        pct   = min(self.bottle_count / KIOSK_CAPACITY, 1.0)
        fill  = int(w * pct)
        color = GREEN_BRIGHT if pct < 0.7 else (AMBER if pct < 0.9 else RED_BRIGHT)
        pygame.draw.rect(self.screen, BG_CARD, (x, y, w, h), border_radius=3)
        if fill > 0:
            pygame.draw.rect(self.screen, color, (x, y, fill, h), border_radius=3)
        pygame.draw.rect(self.screen, GRAY, (x, y, w, h), 1, border_radius=3)
        self.draw_text(f"Bin {self.bottle_count}/{KIOSK_CAPACITY}", self.f_xs, GRAY_LIGHT, x + w + 6, y)

    def draw_keyboard(self, y_start):
        """Render virtual keyboard and return {key: Rect} for hit-testing."""
        rects    = {}
        avail_w  = SCREEN_W - 2 * KB_LEFT

        for row_i, row in enumerate(KB_ROWS):
            ky = y_start + row_i * (KB_KEY_H + KB_GAP)

            if row_i == 3:
                # Last row: normal keys + wide OK button
                normal = row[:-1]
                base_w = KB_KEY_W
                ok_w   = avail_w - len(normal) * (base_w + KB_GAP)
                for col_i, key in enumerate(normal):
                    kx = KB_LEFT + col_i * (base_w + KB_GAP)
                    bg = RED_DIM if key == 'CLR' else BG_CARD
                    pygame.draw.rect(self.screen, bg, (kx, ky, base_w, KB_KEY_H), border_radius=4)
                    pygame.draw.rect(self.screen, GRAY, (kx, ky, base_w, KB_KEY_H), 1, border_radius=4)
                    s = self.f_kb.render(key, True, WHITE)
                    self.screen.blit(s, s.get_rect(center=(kx + base_w // 2, ky + KB_KEY_H // 2)))
                    rects[key] = pygame.Rect(kx, ky, base_w, KB_KEY_H)
                ok_x = KB_LEFT + len(normal) * (base_w + KB_GAP)
                pygame.draw.rect(self.screen, GREEN_DIM,    (ok_x, ky, ok_w, KB_KEY_H), border_radius=4)
                pygame.draw.rect(self.screen, GREEN_BRIGHT, (ok_x, ky, ok_w, KB_KEY_H), 1, border_radius=4)
                s = self.f_kb.render("OK", True, WHITE)
                self.screen.blit(s, s.get_rect(center=(ok_x + ok_w // 2, ky + KB_KEY_H // 2)))
                rects['OK'] = pygame.Rect(ok_x, ky, ok_w, KB_KEY_H)
            else:
                n      = len(row)
                key_w  = (avail_w - (n - 1) * KB_GAP) // n
                for col_i, key in enumerate(row):
                    kx = KB_LEFT + col_i * (key_w + KB_GAP)
                    bg = RED_DIM if key == '<' else BG_CARD
                    pygame.draw.rect(self.screen, bg, (kx, ky, key_w, KB_KEY_H), border_radius=4)
                    pygame.draw.rect(self.screen, GRAY, (kx, ky, key_w, KB_KEY_H), 1, border_radius=4)
                    s = self.f_kb.render(key, True, WHITE)
                    self.screen.blit(s, s.get_rect(center=(kx + key_w // 2, ky + KB_KEY_H // 2)))
                    rects[key] = pygame.Rect(kx, ky, key_w, KB_KEY_H)
        return rects

    # ─── SCREENS ───────────────────────────────────────────────────────────────
    def render_home(self):
        self.draw_scanline_bg()
        self.draw_header_bar("SMART RECYCLING KIOSK")

        self.draw_text("♻  EcoLens", self.f_lg, GREEN_BRIGHT, SCREEN_W // 2, 42, center=True)
        self.draw_text("Dispose plastics · Earn points · Get airtime",
                       self.f_xs, GRAY_LIGHT, SCREEN_W // 2, 64, center=True)

        # User code input box
        self.draw_text("Enter your User Code:", self.f_sm, GRAY_LIGHT, KB_LEFT, 80)
        bx, by, bw, bh = KB_LEFT, 95, SCREEN_W - 2 * KB_LEFT, 32
        pygame.draw.rect(self.screen, BG_CARD, (bx, by, bw, bh), border_radius=5)
        pygame.draw.rect(self.screen, TEAL if self.user_id_input else GRAY,
                         (bx, by, bw, bh), 2, border_radius=5)
        cursor  = "|" if (self.anim_tick // 15) % 2 == 0 else " "
        self.draw_text(self.user_id_input + cursor, self.f_mono, WHITE,
                       SCREEN_W // 2, by + 7, center=True)

        if self.status_msg:
            self.draw_text(self.status_msg, self.f_sm, self.status_color,
                           SCREEN_W // 2, 132, center=True)

        # Virtual keyboard
        self.kb_rects = self.draw_keyboard(140)

    def render_session(self):
        self.draw_scanline_bg()
        self.draw_header_bar("ACTIVE SESSION", show_user=True)

        # Stats bar
        pygame.draw.rect(self.screen, BG_CARD, (0, 37, SCREEN_W, 30))
        self.draw_text(f"Scanned: {self.total_items}",   self.f_sm, GRAY_LIGHT,   8, 46)
        self.draw_text(f"Accepted: {self.accepted_items}", self.f_sm, GREEN_BRIGHT, 130, 46)
        self.draw_text(f"Points: {self.total_points}",   self.f_sm, AMBER,        280, 46)
        pygame.draw.line(self.screen, GREEN_DIM, (0, 67), (SCREEN_W, 67), 1)

        # Camera preview area
        cam_x, cam_y, cam_w, cam_h = 10, 75, 190, 138
        pulse_c = int(30 + 20 * self.pulse)
        pygame.draw.rect(self.screen, (0, pulse_c, 12), (cam_x, cam_y, cam_w, cam_h), border_radius=6)
        pygame.draw.rect(self.screen, GREEN_DIM,         (cam_x, cam_y, cam_w, cam_h), 1, border_radius=6)
        self.draw_text("[ CAMERA ]",        self.f_sm, GREEN_DIM, cam_x + cam_w // 2, cam_y + 52, center=True)
        self.draw_text("Place item in view", self.f_sm, GRAY,     cam_x + cam_w // 2, cam_y + 72, center=True)
        self.draw_text("then tap DISPOSE",  self.f_sm, GRAY,     cam_x + cam_w // 2, cam_y + 90, center=True)

        # Capacity bar below camera
        self.draw_capacity_bar(cam_x, cam_y + cam_h + 5, cam_w, 10)

        # Action buttons
        bx = 212
        self.btn_dispose = self.draw_button("DISPOSE",     bx, 78, 260, 52, GREEN_BRIGHT, BLACK, radius=8)
        self.btn_end     = self.draw_button("END SESSION", bx, 142, 260, 38, RED_DIM, WHITE, radius=8)

        self.draw_text("1. Place item in camera view", self.f_xs, GRAY_LIGHT, bx, 192)
        self.draw_text("2. Tap DISPOSE",               self.f_xs, GRAY_LIGHT, bx, 206)
        self.draw_text("3. Wait for result",           self.f_xs, GRAY_LIGHT, bx, 220)

        pygame.draw.line(self.screen, GREEN_DIM, (0, 258), (SCREEN_W, 258), 1)
        self.draw_text("Session in progress — dispose items one at a time",
                       self.f_xs, GRAY, SCREEN_W // 2, 265, center=True)

    def render_capturing(self):
        self.draw_scanline_bg()
        self.draw_header_bar("ANALYSING")
        cx, cy = SCREEN_W // 2, 138
        for i in range(3):
            r      = 30 + i * 15
            offset = (self.anim_tick * (2 + i)) % 360
            start  = math.radians(offset)
            end    = math.radians(offset + 240)
            pts    = [(cx + r * math.cos(start + (end - start) * s / 60),
                       cy + r * math.sin(start + (end - start) * s / 60))
                      for s in range(60)]
            if len(pts) > 1:
                pygame.draw.lines(self.screen, GREEN_BRIGHT, False, pts, 2)
        self.draw_text("Analysing item...",  self.f_lg, WHITE,      cx, 185, center=True)
        self.draw_text("Please hold still.", self.f_sm, GRAY_LIGHT, cx, 213, center=True)
        for i in range(5):
            lit = ((self.anim_tick // 8) % 5) == i
            pygame.draw.circle(self.screen,
                                GREEN_BRIGHT if lit else GRAY,
                                (cx - 40 + i * 20, 246),
                                5 if lit else 4)

    def render_result(self):
        self.draw_scanline_bg()
        self.draw_header_bar("RESULT", show_user=True)

        if self.result_valid:
            main_color, bg_color = GREEN_BRIGHT, (0, 40, 20)
            icon, headline = "OK", "ACCEPTED"
        else:
            main_color, bg_color = RED_BRIGHT, (40, 10, 10)
            icon, headline = "X", "REJECTED"

        pygame.draw.rect(self.screen, bg_color,   (12, 42, SCREEN_W - 24, 116), border_radius=10)
        pygame.draw.rect(self.screen, main_color, (12, 42, SCREEN_W - 24, 116), 2, border_radius=10)
        self.draw_text(icon,                             self.f_xl, main_color, 36,          66)
        self.draw_text(headline,                         self.f_lg, main_color, 80,          58)
        self.draw_text(f"Item: {self.result_label.upper()}", self.f_md, WHITE,  80,          88)
        conf_pct = f"{self.result_conf * 100:.0f}%" if self.result_conf <= 1 else f"{self.result_conf:.0f}%"
        self.draw_text(f"Confidence: {conf_pct}",        self.f_sm, GRAY_LIGHT, 80,         112)
        if self.result_valid:
            self.draw_text(f"+{self.result_points} pts", self.f_lg, AMBER,  SCREEN_W - 70,  66)
            self.draw_text(f"Total: {self.total_points}", self.f_sm, GRAY_LIGHT, SCREEN_W - 70, 98)

        # Buttons
        is_now_full = self.result_valid and self.bottle_count >= KIOSK_CAPACITY
        if is_now_full:
            # Disable dispose again — kiosk is full
            pygame.draw.rect(self.screen, (30, 30, 30), (12, 172, 210, 42), border_radius=8)
            pygame.draw.rect(self.screen, GRAY,         (12, 172, 210, 42), 1, border_radius=8)
            self.draw_text("KIOSK FULL", self.f_md, GRAY, 12 + 105, 172 + 13, center=True)
            self.btn_dispose_again = None
        else:
            self.btn_dispose_again = self.draw_button(
                "DISPOSE AGAIN", 12, 172, 210, 42, GREEN_DIM, WHITE, radius=8)

        self.btn_end_from_result = self.draw_button(
            "END SESSION", 234, 172, 234, 42, RED_DIM, WHITE, radius=8)

        # Footer bar
        pygame.draw.rect(self.screen, BG_CARD, (0, 228, SCREEN_W, 32))
        pygame.draw.line(self.screen, GREEN_DIM, (0, 228), (SCREEN_W, 228), 1)
        rem = KIOSK_CAPACITY - self.bottle_count
        self.draw_text(
            f"Bin: {self.bottle_count}/{KIOSK_CAPACITY}  ·  "
            f"{rem} slot{'s' if rem != 1 else ''} remaining",
            self.f_xs, GRAY_LIGHT, SCREEN_W // 2, 236, center=True)
        self.draw_text(
            f"Session: {self.accepted_items} accepted  ·  {self.total_points} pts",
            self.f_xs, GRAY_LIGHT, SCREEN_W // 2, 250, center=True)
        if not is_now_full:
            self.draw_text(
                "Tap DISPOSE AGAIN or END SESSION",
                self.f_xs, GRAY, SCREEN_W // 2, 264, center=True)

    def render_full(self):
        self.draw_scanline_bg()
        self.draw_header_bar("KIOSK STATUS")

        # Auto-poll every 60 s
        if time.time() - self.last_full_check > 60:
            threading.Thread(target=self._check_if_admin_reset, daemon=True).start()

        cx = SCREEN_W // 2
        pygame.draw.rect(self.screen, (50, 10, 10), (cx - 70, 46, 140, 72), border_radius=10)
        pygame.draw.rect(self.screen, RED_BRIGHT,   (cx - 70, 46, 140, 72), 2, border_radius=10)
        self.draw_text("!",    self.f_xl, RED_BRIGHT, cx, 52, center=True)
        self.draw_text("FULL", self.f_lg, RED_BRIGHT, cx, 90, center=True)

        self.draw_text("KIOSK IS AT CAPACITY",                     self.f_md, WHITE,      cx, 132, center=True)
        self.draw_text(f"{self.bottle_count} of {KIOSK_CAPACITY} bottles collected.",
                       self.f_sm, GRAY_LIGHT, cx, 154, center=True)
        self.draw_text("Contact admin to empty this unit.",         self.f_sm, GRAY_LIGHT, cx, 170, center=True)

        if UNIT_ID != "YOUR-UNIT-UUID-HERE":
            self.draw_text(f"Unit ID: {UNIT_ID[:8]}...", self.f_xs, GRAY, cx, 188, center=True)

        # Manual check button
        self.btn_check_status = self.draw_button(
            "Check Status", cx - 80, 206, 160, 36, BG_CARD, TEAL, radius=8)
        pygame.draw.rect(self.screen, TEAL, (cx - 80, 206, 160, 36), 1, border_radius=8)

        elapsed    = int(time.time() - self.last_full_check)
        if elapsed < 5:
            check_txt = "Checking..."
        else:
            next_auto = max(0, 60 - elapsed)
            check_txt = f"Auto-check in {next_auto}s"
        self.draw_text(check_txt, self.f_xs, GRAY, cx, 254, center=True)
        self.draw_text("Admin: reset via EcoLens dashboard → kiosk → Reset Capacity",
                       self.f_xs, GRAY, cx, 270, center=True)

    def render_loading(self):
        self.draw_scanline_bg()
        self.draw_header_bar("PLEASE WAIT")
        self.draw_text(self.status_msg, self.f_lg, WHITE, SCREEN_W // 2, 126, center=True)
        cx, cy = SCREEN_W // 2, 186
        for i in range(8):
            angle = math.radians(i * 45 + self.anim_tick * 4)
            x = cx + int(22 * math.cos(angle))
            y = cy + int(22 * math.sin(angle))
            v = max(60, 255 - i * 28)
            pygame.draw.circle(self.screen, (0, v, v // 2), (x, y), 4 if i == 0 else 3)

    # ─── INPUT ─────────────────────────────────────────────────────────────────
    def handle_keyboard_char(self, char):
        if char in ('<', 'BACKSPACE'):
            self.user_id_input = self.user_id_input[:-1]
        elif char == 'CLR':
            self.user_id_input = ""
        elif char in ('OK', 'ENTER'):
            if self.user_id_input:
                if self.bottle_count >= KIOSK_CAPACITY:
                    self.state = "full"
                    return
                self.user_code    = self.user_id_input.strip().upper()
                self.status_msg   = ""
                self.status_color = WHITE
                threading.Thread(target=self.api_start_session, daemon=True).start()
        else:
            if len(self.user_id_input) < 12:
                self.user_id_input += char.upper()

    def handle_key(self, event):
        if self.state != "home":
            return
        if event.key == pygame.K_BACKSPACE:
            self.handle_keyboard_char('BACKSPACE')
        elif event.key == pygame.K_RETURN:
            self.handle_keyboard_char('ENTER')
        elif event.key == pygame.K_DELETE:
            self.handle_keyboard_char('CLR')
        elif event.unicode and event.unicode.isalnum():
            self.handle_keyboard_char(event.unicode)
        self.status_msg = ""

    def handle_click(self, pos):
        mx, my = pos

        if self.state == "home":
            for key, rect in self.kb_rects.items():
                if rect.collidepoint(mx, my):
                    self.handle_keyboard_char(key)
                    break

        elif self.state == "session":
            if hasattr(self, "btn_dispose") and self.btn_dispose.collidepoint(mx, my):
                if self.bottle_count >= KIOSK_CAPACITY:
                    self.state = "full"
                else:
                    threading.Thread(target=self.api_capture_and_classify, daemon=True).start()
            elif hasattr(self, "btn_end") and self.btn_end.collidepoint(mx, my):
                threading.Thread(target=self.api_end_session, daemon=True).start()

        elif self.state == "result":
            if self.btn_dispose_again and self.btn_dispose_again.collidepoint(mx, my):
                # Go back to session screen; user positions item before tapping DISPOSE
                self.state = "session"
            elif self.btn_end_from_result and self.btn_end_from_result.collidepoint(mx, my):
                threading.Thread(target=self.api_end_session, daemon=True).start()

        elif self.state == "full":
            if self.btn_check_status and self.btn_check_status.collidepoint(mx, my):
                self.last_full_check = time.time()
                threading.Thread(target=self._check_if_admin_reset, daemon=True).start()

    # ─── MAIN LOOP ─────────────────────────────────────────────────────────────
    def run(self):
        if self.bottle_count >= KIOSK_CAPACITY:
            self.state = "full"

        while True:
            self.anim_tick += 1
            self.pulse     += 0.04 * self.pulse_dir
            if self.pulse >= 1.0 or self.pulse <= 0.0:
                self.pulse_dir *= -1

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.cleanup()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.cleanup()
                    self.handle_key(event)
                if event.type == pygame.MOUSEBUTTONDOWN:
                    self.handle_click(event.pos)
                if event.type == pygame.FINGERDOWN:
                    self.handle_click((int(event.x * SCREEN_W), int(event.y * SCREEN_H)))

            {
                "home":      self.render_home,
                "session":   self.render_session,
                "capturing": self.render_capturing,
                "result":    self.render_result,
                "full":      self.render_full,
                "loading":   self.render_loading,
            }.get(self.state, self.render_home)()

            pygame.display.flip()
            self.clock.tick(FPS)

    def cleanup(self):
        if self.camera:
            try:
                self.camera.stop()
            except Exception:
                pass
        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    kiosk = EcoLensKiosk()
    kiosk.run()
