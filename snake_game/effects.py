"""Effets visuels : particules, textes flottants, tremblement, fond animé, transitions."""
import math
import random

import pygame

from . import ui
from .ui import S


class Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "size", "color", "gravity", "drag", "glow")


class ParticleSystem:
    def __init__(self, limit=1500):
        self.items = []
        self.limit = limit

    def burst(self, x, y, color, count=16, speed=(60, 220), size=(2, 5), life=(0.4, 0.9),
              gravity=0.0, drag=2.5, glow=False, angle=None, spread=math.tau):
        for _ in range(count):
            if len(self.items) >= self.limit:
                return
            a = random.uniform(0, math.tau) if angle is None else angle + random.uniform(-spread / 2, spread / 2)
            sp = random.uniform(*speed)
            p = Particle()
            p.x, p.y = x, y
            p.vx, p.vy = math.cos(a) * sp, math.sin(a) * sp
            p.life = p.max_life = random.uniform(*life)
            p.size = random.uniform(*size)
            p.color = color
            p.gravity, p.drag, p.glow = gravity, drag, glow
            self.items.append(p)

    def update(self, dt):
        alive = []
        for p in self.items:
            p.life -= dt
            if p.life <= 0:
                continue
            k = max(0.0, 1 - p.drag * dt)
            p.vx *= k
            p.vy = p.vy * k + p.gravity * dt
            p.x += p.vx * dt
            p.y += p.vy * dt
            alive.append(p)
        self.items = alive

    def draw(self, surf, origin=(0, 0)):
        ox, oy = origin
        for p in self.items:
            k = p.life / p.max_life
            r = max(1.0, p.size * k)
            pos = (p.x + ox, p.y + oy)
            if p.glow:
                ui.blit_glow(surf, pos, r * 3.5, ui.darken(p.color, 0.5))
            pygame.draw.circle(surf, p.color, pos, r)

    def clear(self):
        self.items.clear()


class FloatingTexts:
    """Petits textes « +10 », « COMBO x3 » qui montent puis s'effacent."""

    def __init__(self):
        self.items = []

    def add(self, text, x, y, color, size=26, life=0.9):
        self.items.append({"text": text, "x": x, "y": y, "color": color, "size": size,
                           "life": life, "max": life})

    def update(self, dt):
        for t in self.items:
            t["life"] -= dt
            t["y"] -= S(55) * dt
        self.items = [t for t in self.items if t["life"] > 0]

    def draw(self, surf, origin=(0, 0)):
        for t in self.items:
            k = t["life"] / t["max"]
            pop = ui.ease_out_back(min(1.0, (1 - k) * 5))
            size = max(8, int(S(t["size"]) * (0.6 + 0.4 * pop)))
            ui.draw_text(surf, t["text"], size, t["color"], (t["x"] + origin[0], t["y"] + origin[1]),
                         bold=True, alpha=int(255 * min(1.0, k * 2)))


class ScreenShake:
    def __init__(self):
        self.power = 0.0

    def add(self, amount):
        self.power = min(30.0, self.power + amount)

    def update(self, dt):
        self.power *= math.exp(-7 * dt)
        if self.power < 0.3:
            self.power = 0.0

    def offset(self):
        if self.power <= 0:
            return 0, 0
        p = S(self.power)
        return random.randint(-p, p), random.randint(-p, p)


class Background:
    """Dégradé + vignette + orbes lumineuses qui dérivent lentement."""

    def __init__(self, count=14):
        self.key = None
        self.surface = None
        self.time = 0.0
        self.orbs = [{"x": random.random(), "y": random.random(), "r": random.uniform(60, 170),
                      "vx": random.uniform(-0.012, 0.012), "vy": random.uniform(-0.02, -0.004),
                      "phase": random.uniform(0, math.tau), "color": random.choice(("accent", "accent2", "snake_tail"))}
                     for _ in range(count)]

    def update(self, dt):
        self.time += dt
        for o in self.orbs:
            o["x"] = (o["x"] + o["vx"] * dt) % 1.0
            o["y"] = (o["y"] + o["vy"] * dt) % 1.0

    def _build(self, size, theme):
        surf = ui.vertical_gradient(size, theme["bg_top"], theme["bg_bottom"])
        # Vignette calculée en petit puis agrandie (rapide et doux)
        small = pygame.Surface((64, 36), pygame.SRCALPHA)
        for y in range(36):
            for x in range(64):
                d = math.hypot((x - 31.5) / 32, (y - 17.5) / 18)
                small.set_at((x, y), (0, 0, 0, int(200 * ui.clamp(d - 0.45) ** 1.5)))
        surf.blit(pygame.transform.smoothscale(small, size), (0, 0))
        return surf

    def draw(self, surf, theme):
        size = surf.get_size()
        key = (size, theme["name"])
        if key != self.key:
            self.key = key
            self.surface = self._build(size, theme)
        surf.blit(self.surface, (0, 0))
        w, h = size
        for o in self.orbs:
            pulse = 0.65 + 0.35 * math.sin(self.time * 0.8 + o["phase"])
            color = ui.darken(theme[o["color"]], 0.86 - 0.06 * pulse)
            ui.blit_glow(surf, (o["x"] * w, o["y"] * h), S(o["r"]), color)


class Transition:
    """Rideau de carrés en diagonale : ferme l'écran, exécute le callback, puis rouvre."""

    HALF = 0.42

    def __init__(self, callback):
        self.callback = callback
        self.phase = "out"
        self.t = 0.0
        self.done = False

    def update(self, dt):
        self.t += dt / self.HALF
        if self.t >= 1.0:
            if self.phase == "out":
                self.callback()
                self.phase = "in"
                self.t = 0.0
            else:
                self.done = True

    def draw(self, surf, theme):
        w, h = surf.get_size()
        tile = max(16, S(46))
        cols, rows = w // tile + 1, h // tile + 1
        span = cols + rows
        for j in range(rows):
            for i in range(cols):
                delay = (i + j) / span * 0.5
                local = ui.clamp((self.t - delay) / 0.5)
                cover = ui.ease_in_out(local) if self.phase == "out" else 1 - ui.ease_in_out(local)
                if cover <= 0.01:
                    continue
                size = int(tile * cover) + 2
                color = ui.lerp_color(theme["accent"], theme["bg_top"], 0.35 + 0.65 * cover)
                rect = pygame.Rect(0, 0, size, size)
                rect.center = (i * tile + tile // 2, j * tile + tile // 2)
                pygame.draw.rect(surf, color, rect, border_radius=int(tile * 0.3 * (1 - cover)))
