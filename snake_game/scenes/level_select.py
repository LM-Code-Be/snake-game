"""Sélection du niveau (mode Aventure) avec miniatures, étoiles et cadenas."""
import math

import pygame

from .. import ui
from ..config import GOLD
from ..levels import LEVELS, MAX_LEVEL
from ..renderer import draw_level_preview
from ..ui import S
from .base import Scene

GRID_COLS = 5


class LevelSelectScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.progress = app.db.level_progress()
        self.unlocked = app.db.unlocked_level(MAX_LEVEL)
        self.selected = self.unlocked - 1
        self.cards = []
        self.hover = [0.0] * MAX_LEVEL

    def start(self, index):
        if index + 1 > self.unlocked:
            self.app.audio.play("pause")
            return
        from .game import GameScene
        self.app.audio.play("click")
        self.app.change_scene(lambda: GameScene(self.app, mode="aventure", level=index + 1))

    def move(self, dx, dy):
        col, row = self.selected % GRID_COLS, self.selected // GRID_COLS
        col = (col + dx) % GRID_COLS
        row = (row + dy) % (MAX_LEVEL // GRID_COLS)
        new = row * GRID_COLS + col
        if new != self.selected:
            self.selected = new
            self.app.audio.play("hover")

    def handle_event(self, event):
        if self.is_back(event):
            self.go_menu()
        elif event.type == pygame.KEYDOWN:
            moves = {pygame.K_LEFT: (-1, 0), pygame.K_q: (-1, 0), pygame.K_a: (-1, 0),
                     pygame.K_RIGHT: (1, 0), pygame.K_d: (1, 0),
                     pygame.K_UP: (0, -1), pygame.K_z: (0, -1), pygame.K_w: (0, -1),
                     pygame.K_DOWN: (0, 1), pygame.K_s: (0, 1)}
            if event.key in moves:
                self.move(*moves[event.key])
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                self.start(self.selected)
        elif event.type == pygame.MOUSEMOTION:
            for i, rect in enumerate(self.cards):
                if rect.collidepoint(event.pos) and i != self.selected:
                    self.selected = i
                    self.app.audio.play("hover")
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, rect in enumerate(self.cards):
                if rect.collidepoint(event.pos):
                    self.start(i)

    def update(self, dt):
        super().update(dt)
        for i in range(MAX_LEVEL):
            target = 1.0 if i == self.selected else 0.0
            self.hover[i] += (target - self.hover[i]) * min(1.0, dt * 12)

    def draw(self, surf):
        super().draw(surf)
        theme = self.theme
        w, h = surf.get_size()
        self.draw_title(surf, "AVENTURE", S(70))
        stars = sum(p["stars"] for p in self.progress.values())
        ui.draw_text(surf, f"★ {stars} / {MAX_LEVEL * 3}", S(20), GOLD, (w // 2, S(122)), bold=True)

        rows = MAX_LEVEL // GRID_COLS
        gap = S(20)
        card_w = min(S(210), (w - S(80) - gap * (GRID_COLS - 1)) // GRID_COLS)
        card_h = card_w
        total_w = GRID_COLS * card_w + (GRID_COLS - 1) * gap
        total_h = rows * card_h + (rows - 1) * gap
        top = max(S(150), (h - total_h) // 2 + S(40))
        left = (w - total_w) // 2
        self.cards = []
        for i, level in enumerate(LEVELS):
            col, row = i % GRID_COLS, i // GRID_COLS
            rect = pygame.Rect(left + col * (card_w + gap), top + row * (card_h + gap), card_w, card_h)
            self.cards.append(rect)
            appear = ui.ease_out_back((self.time - i * 0.04) / 0.45)
            if appear <= 0:
                continue
            self._draw_card(surf, rect, level, i, appear)

        level = LEVELS[self.selected]
        info_y = top + total_h + S(34)
        if info_y < h - S(50):
            text = level.description if self.selected < self.unlocked else "Terminez le niveau précédent pour débloquer celui-ci."
            ui.draw_text(surf, text, S(19), theme["text"], (w // 2, info_y))
        self.draw_hint(surf, "Flèches  choisir     Entrée  jouer     Échap  retour")

    def _draw_card(self, surf, rect, level, i, appear):
        theme = self.theme
        locked = i + 1 > self.unlocked
        hv = self.hover[i]
        rect = rect.inflate(int(S(12) * hv), int(S(12) * hv))
        rect.y -= int(S(6) * hv)
        if appear < 1:
            rect = rect.inflate(-int(rect.w * (1 - appear)), -int(rect.h * (1 - appear)))
        if hv > 0.05 and not locked:
            ui.blit_glow(surf, rect.center, int(rect.w * 0.75), ui.darken(theme["accent"], 1 - 0.3 * hv))
        border = ui.lerp_color(ui.lighten(theme["panel"], 0.1), theme["accent"], hv)
        ui.draw_panel(surf, rect, theme["panel"], 240, S(16), (*border, 255), S(2))
        if rect.w < S(40):
            return
        preview = pygame.Rect(rect.x + S(12), rect.y + S(40), rect.w - S(24), int((rect.w - S(24)) * 0.55))
        draw_level_preview(surf, level, preview, theme)
        ui.draw_text(surf, f"{level.number}", S(22), theme["accent"], (rect.x + S(16), rect.y + S(20)),
                     anchor="midleft", bold=True)
        ui.draw_text(surf, level.name, S(16), theme["text"], (rect.right - S(12), rect.y + S(20)),
                     anchor="midright", bold=True)
        info = self.progress.get(level.number)
        by = preview.bottom + S(24)
        for s in range(3):
            filled = info is not None and s < info["stars"]
            ui.draw_star(surf, (rect.centerx + (s - 1) * S(26), by), S(10),
                         GOLD if filled else ui.darken(theme["panel"], 0.45))
        sub = f"Record : {info['best']}" if info else f"{level.target} pommes · {'bords ouverts' if level.wrap else 'murs'}"
        ui.draw_text(surf, sub, S(13), theme["text_dim"], (rect.centerx, by + S(24)))
        if locked:
            veil = pygame.Surface(rect.size, pygame.SRCALPHA)
            pygame.draw.rect(veil, (0, 0, 0, 150), veil.get_rect(), border_radius=S(16))
            surf.blit(veil, rect)
            bob = math.sin(self.time * 3 + i) * S(3)
            ui.draw_padlock(surf, (rect.centerx, rect.centery + bob), S(44), theme["text_dim"])
