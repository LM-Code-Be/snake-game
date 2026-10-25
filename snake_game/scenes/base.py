"""Classe de base des scènes (menu, jeu, scores...)."""
import math

import pygame

from .. import ui
from ..ui import S


class Scene:
    def __init__(self, app):
        self.app = app
        self.time = 0.0

    @property
    def theme(self):
        return self.app.theme

    def handle_event(self, event):
        pass

    def update(self, dt):
        self.time += dt

    def draw(self, surf):
        self.app.background.draw(surf, self.theme)

    def on_exit(self):
        """Appelé quand on quitte la scène (changement d'écran)."""

    def on_quit(self):
        """Appelé quand l'application se ferme alors que la scène est active."""

    # --- Helpers communs ----------------------------------------------------------
    def is_back(self, event):
        return (event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE)) or \
               (event.type == pygame.MOUSEBUTTONDOWN and event.button == 3)

    def go_menu(self):
        from .menu import MenuScene
        self.app.change_scene(lambda: MenuScene(self.app))

    def draw_title(self, surf, text, y, size=64):
        w = surf.get_width()
        appear = ui.ease_out_back(self.time / 0.6)
        size = max(10, int(S(size) * (0.7 + 0.3 * appear)))
        ui.blit_glow(surf, (w // 2, y), int(size * 1.6), ui.darken(self.theme["accent"], 0.75))
        ui.draw_text(surf, text, size, self.theme["text"], (w // 2, y), bold=True,
                     alpha=int(255 * ui.clamp(self.time / 0.3)))

    def draw_hint(self, surf, text):
        w, h = surf.get_size()
        alpha = int(150 + 80 * math.sin(self.time * 3))
        ui.draw_text(surf, text, S(17), self.theme["text_dim"], (w // 2, h - S(28)), alpha=alpha)
