"""Écran de fin de partie : score, statistiques, record et saisie du nom."""
import math
import random

import pygame

from .. import ui
from ..config import GOLD
from ..effects import ParticleSystem
from ..ui import S, Button, Menu, TextInput
from .base import Scene


def format_duration(seconds):
    seconds = int(seconds)
    return f"{seconds // 60}:{seconds % 60:02d}"


class GameOverScene(Scene):
    def __init__(self, app, result):
        super().__init__(app)
        self.result = result
        self.score = result["score"]
        self.new_record = self.score > result["record"] and self.score > 0
        self.rank = app.db.rank_of(result["mode"], self.score)
        self.saved = False
        self.particles = ParticleSystem()
        self.input = None
        if self.score > 0 and self.rank <= 10:
            self.input = TextInput(app.settings["player"])
            pygame.key.start_text_input()
        else:
            self._save(app.settings["player"])
        app.audio.play("level" if result["victory"] else "gameover")

        replay_label = "Choisir un niveau" if result["mode"] == "aventure" else "Rejouer"
        self.menu = Menu(app, [Button(replay_label, self.replay), Button("Menu principal", self.go_menu)],
                         width=340, height=54, gap=10)

    def _save(self, name):
        if self.saved:
            return
        name = name.strip() or "Joueur"
        self.app.db.add_score(name, self.result)
        if name != self.app.settings["player"]:
            self.app.set_setting("player", name)
        self.saved = True

    def replay(self):
        if self.result["mode"] == "aventure":
            from .level_select import LevelSelectScene
            self.app.change_scene(lambda: LevelSelectScene(self.app))
        else:
            from .game import GameScene
            self.app.change_scene(lambda: GameScene(self.app, mode="classique"))

    def handle_event(self, event):
        if not self.saved and self.input is not None:
            if self.input.handle_event(event) == "submit":
                self.app.audio.play("click")
                pygame.key.stop_text_input()
                self._save(self.input.text)
                self.menu.age = 0.0
            return
        self.menu.handle_event(event)

    def update(self, dt):
        super().update(dt)
        self.menu.update(dt)
        self.particles.update(dt)
        if (self.result["victory"] or self.new_record) and self.time < 4 and random.random() < dt * 10:
            w = self.app.screen.get_width()
            color = random.choice((self.theme["accent"], self.theme["accent2"], GOLD, self.theme["snake_head"]))
            self.particles.burst(random.uniform(0, w), -S(10), color, 12, (S(40), S(200)), (S(2), S(5)),
                                 (1.5, 2.5), gravity=S(300), drag=1.2)

    def on_exit(self):
        self._save(self.input.text if self.input else self.app.settings["player"])
        pygame.key.stop_text_input()

    def on_quit(self):
        self.on_exit()

    def draw(self, surf):
        super().draw(surf)
        theme = self.theme
        w, h = surf.get_size()
        cx = w // 2
        victory = self.result["victory"]
        title = "VICTOIRE !" if victory else "GAME OVER"
        color = GOLD if victory else theme["danger"]
        appear = ui.ease_out_back(self.time / 0.6)
        size = max(10, int(S(78) * (0.6 + 0.4 * appear)))
        ui.blit_glow(surf, (cx, S(90)), S(200), ui.darken(color, 0.7))
        ui.draw_text(surf, title, size, color, (cx, S(90)), bold=True)

        # Score qui défile
        k = ui.ease_out_cubic((self.time - 0.3) / 1.2)
        ui.draw_text(surf, "SCORE", S(18), theme["text_dim"], (cx, S(160)), bold=True)
        ui.draw_text(surf, str(int(self.score * k)), S(64), theme["text"], (cx, S(206)), bold=True)
        if self.new_record and self.time > 1.4:
            pulse = 1 + 0.06 * math.sin(self.time * 6)
            ui.draw_text(surf, "★ NOUVEAU RECORD ★", int(S(24) * pulse), GOLD, (cx, S(256)), bold=True)
        elif self.rank <= 10 and self.score > 0 and self.time > 1.4:
            ui.draw_text(surf, f"{self.rank}e du classement", S(20), theme["accent"], (cx, S(256)), bold=True)

        # Statistiques de la partie
        r = self.result
        mode = "Aventure" if r["mode"] == "aventure" else "Classique"
        stats = [
            ("Mode", mode), ("Niveau", str(r["level"]) if r["mode"] == "aventure" else "-"),
            ("Pommes", str(r["apples"])), ("Longueur max", str(r["length"])),
            ("Combo max", f"x{r['max_combo']}"), ("Durée", format_duration(r["duration"])),
        ]
        card_w, card_h, gap = S(170), S(70), S(14)
        total = 3 * card_w + 2 * gap
        for i, (label, value) in enumerate(stats):
            appear = ui.ease_out_cubic((self.time - 0.5 - i * 0.07) / 0.4)
            if appear <= 0:
                continue
            col, row = i % 3, i // 3
            rect = pygame.Rect(cx - total // 2 + col * (card_w + gap), S(290) + row * (card_h + gap), card_w, card_h)
            rect.y += int((1 - appear) * S(30))
            ui.draw_panel(surf, rect, theme["panel"], int(220 * appear), S(14))
            ui.draw_text(surf, label, S(15), theme["text_dim"], (rect.centerx, rect.y + S(20)), alpha=int(255 * appear))
            ui.draw_text(surf, value, S(26), theme["text"], (rect.centerx, rect.y + S(47)), bold=True,
                         alpha=int(255 * appear))

        bottom = S(290) + 2 * card_h + gap + S(30)
        if not self.saved and self.input is not None:
            ui.draw_text(surf, "Entrez votre nom pour le classement :", S(20), theme["accent"], (cx, bottom + S(10)))
            box = pygame.Rect(0, 0, S(360), S(56))
            box.midtop = (cx, bottom + S(30))
            self.input.draw(surf, box, theme, self.time)
            self.draw_hint(surf, "Entrée pour valider")
        else:
            self.menu.layout(cx, bottom + S(10))
            self.menu.draw(surf, theme)
        self.particles.draw(surf)
