"""Menu principal : titre animé, serpent de démonstration et navigation."""
import math

import pygame

from .. import ui
from ..config import VERSION
from ..levels import MAX_LEVEL
from ..ui import S, Button, Menu
from .base import Scene


class MenuScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        db = app.db
        self.save = db.load_game()
        sub = None
        if self.save:
            if self.save["mode"] == "aventure":
                sub = f"Aventure · Niveau {self.save['level']} · {self.save['score']} pts"
            else:
                sub = f"Classique · {self.save['score']} pts"
        unlocked = db.unlocked_level(MAX_LEVEL)
        self.menu = Menu(app, [
            Button("Continuer", self.continue_game, enabled=self.save is not None, sub=sub),
            Button("Aventure", self.adventure, sub=f"{unlocked}/{MAX_LEVEL} niveaux débloqués"),
            Button("Mode classique", self.classic, sub="Score infini, vitesse croissante"),
            Button("Scores & statistiques", self.scores),
            Button("Comment jouer", self.help),
            Button("Paramètres", self.settings),
            Button("Quitter", app.quit),
        ], width=420, height=54, gap=10)
        self.best = max(db.best_score("aventure"), db.best_score("classique"))

    # --- Actions -----------------------------------------------------------------
    def continue_game(self):
        from .game import GameScene
        state = self.app.db.load_game()
        if state:
            self.app.change_scene(lambda: GameScene(self.app, saved=state))

    def adventure(self):
        from .level_select import LevelSelectScene
        self.app.change_scene(lambda: LevelSelectScene(self.app))

    def classic(self):
        from .game import GameScene
        self.app.change_scene(lambda: GameScene(self.app, mode="classique"))

    def scores(self):
        from .scores import ScoresScene
        self.app.change_scene(lambda: ScoresScene(self.app))

    def help(self):
        from .help import HelpScene
        self.app.change_scene(lambda: HelpScene(self.app))

    def settings(self):
        from .settings import SettingsScene
        self.app.change_scene(lambda: SettingsScene(self.app))

    # --- Boucle ----------------------------------------------------------------------
    def handle_event(self, event):
        self.menu.handle_event(event)

    def update(self, dt):
        super().update(dt)
        self.menu.update(dt)

    def _draw_demo_snake(self, surf):
        """Serpent décoratif qui suit une courbe de Lissajous en arrière-plan."""
        w, h = surf.get_size()
        theme = self.theme
        n = 46
        for k in range(n - 1, -1, -1):
            t = self.time * 0.55 - k * 0.022
            x = w / 2 + w * 0.43 * math.sin(t * 1.3 + 0.6)
            y = h / 2 + h * 0.4 * math.sin(t * 2.1)
            col = ui.lerp_color(theme["snake_head"], theme["snake_tail"], k / n)
            col = ui.lerp_color(col, theme["bg_bottom"], 0.7)
            pygame.draw.circle(surf, col, (x, y), S(22) * (1 - 0.5 * k / n))

    def _draw_logo(self, surf, y):
        w = surf.get_width()
        theme = self.theme
        size = S(104)
        letters = "SNAKE"
        imgs = [ui.render_text(ch, size, (255, 255, 255), True) for ch in letters]
        spacing = S(6)
        total = sum(i.get_width() for i in imgs) + spacing * (len(imgs) - 1)
        x = w // 2 - total // 2
        ui.blit_glow(surf, (w // 2, y), S(230), ui.darken(theme["accent"], 0.7))
        for i, ch in enumerate(letters):
            appear = ui.ease_out_back((self.time - i * 0.08) / 0.5)
            dy = math.sin(self.time * 3 + i * 0.7) * S(8)
            color = ui.lerp_color(theme["snake_head"], theme["snake_tail"], i / (len(letters) - 1))
            cw = imgs[i].get_width()
            if appear > 0:
                letter = int(size * appear)
                ui.draw_text(surf, ch, max(8, letter), color, (x + cw // 2, y + dy), bold=True)
            x += cw + spacing
        sub_alpha = int(255 * ui.clamp((self.time - 0.5) / 0.5))
        ui.draw_text(surf, "N  É  O  N", S(22), theme["accent2"], (w // 2, y + S(64)), bold=True, alpha=sub_alpha)

    def draw(self, surf):
        super().draw(surf)
        w, h = surf.get_size()
        self._draw_demo_snake(surf)
        title_y = S(100)
        self._draw_logo(surf, title_y)
        top = max(title_y + S(110), h // 2 - self.menu.total_height() // 2 + S(60))
        self.menu.layout(w // 2, top)
        self.menu.draw(surf, self.theme)
        dim = self.theme["text_dim"]
        ui.draw_text(surf, f"Meilleur score : {self.best}", S(18), dim, (S(24), h - S(28)), anchor="midleft")
        ui.draw_text(surf, f"v{VERSION}", S(16), dim, (w - S(24), h - S(28)), anchor="midright")
        self.draw_hint(surf, "↑ ↓  naviguer     Entrée  valider     F11  plein écran")
