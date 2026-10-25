"""Écran des paramètres (sauvegardés immédiatement dans SQLite)."""
import pygame

from .. import config, ui
from ..ui import S, TextInput
from .base import Scene

OPTIONS = [
    {"key": "player", "label": "Nom du joueur", "kind": "text"},
    {"key": "difficulty", "label": "Difficulté", "kind": "choice", "choices": config.DIFFICULTY_ORDER,
     "names": {k: v["label"] for k, v in config.DIFFICULTIES.items()}},
    {"key": "theme", "label": "Thème", "kind": "choice", "choices": config.THEME_ORDER,
     "names": {k: v["label"] for k, v in config.THEMES.items()}},
    {"key": "music_volume", "label": "Musique", "kind": "slider"},
    {"key": "sfx_volume", "label": "Effets sonores", "kind": "slider"},
    {"key": "show_grid", "label": "Afficher la grille", "kind": "toggle"},
    {"key": "screen_shake", "label": "Tremblements d'écran", "kind": "toggle"},
    {"key": "fullscreen", "label": "Plein écran", "kind": "toggle"},
    {"key": "show_fps", "label": "Afficher les FPS", "kind": "toggle"},
    {"key": "reset", "label": "Réinitialiser les données", "kind": "action"},
    {"key": "back", "label": "Retour", "kind": "action"},
]


class SettingsScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.selected = 0
        self.rows = []
        self.hover = [0.0] * len(OPTIONS)
        self.toggles = {o["key"]: float(app.settings[o["key"]]) for o in OPTIONS if o["kind"] == "toggle"}
        self.editing = None
        self.confirm_reset = False
        self.message = ""
        self.message_time = 0.0

    # --- Modification des valeurs ------------------------------------------------
    def change(self, option, step):
        key, kind = option["key"], option["kind"]
        settings = self.app.settings
        if kind == "choice":
            choices = option["choices"]
            value = choices[(choices.index(settings[key]) + step) % len(choices)]
        elif kind == "slider":
            value = max(0, min(10, settings[key] + step))
            if value == settings[key]:
                return
        elif kind == "toggle":
            value = not settings[key]
        else:
            return
        self.app.audio.play("hover")
        self.app.set_setting(key, value)

    def activate(self, option):
        kind, key = option["kind"], option["key"]
        if kind == "text":
            self.editing = TextInput(self.app.settings["player"])
            pygame.key.start_text_input()
            self.app.audio.play("click")
        elif kind in ("choice", "toggle"):
            self.change(option, 1)
        elif key == "back":
            self.app.audio.play("click")
            self.go_menu()
        elif key == "reset":
            self.app.audio.play("click")
            if self.confirm_reset:
                self.app.db.reset_all()
                self.confirm_reset = False
                self.flash("Scores, progression et sauvegarde effacés.")
            else:
                self.confirm_reset = True
                self.flash("Validez une seconde fois pour confirmer.")

    def flash(self, text):
        self.message = text
        self.message_time = 3.0

    def move(self, step):
        self.selected = (self.selected + step) % len(OPTIONS)
        self.confirm_reset = False
        self.app.audio.play("hover")

    # --- Événements -------------------------------------------------------------------
    def handle_event(self, event):
        if self.editing:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self._stop_editing(save=False)
            elif self.editing.handle_event(event) == "submit":
                self._stop_editing(save=True)
            return
        option = OPTIONS[self.selected]
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                self.go_menu()
            elif event.key in (pygame.K_UP, pygame.K_z, pygame.K_w):
                self.move(-1)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.move(1)
            elif event.key in (pygame.K_LEFT, pygame.K_q, pygame.K_a):
                self.change(option, -1)
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                self.change(option, 1)
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                self.activate(option)
        elif event.type == pygame.MOUSEMOTION:
            for i, rect in enumerate(self.rows):
                if rect.collidepoint(event.pos) and i != self.selected:
                    self.selected = i
                    self.confirm_reset = self.confirm_reset and OPTIONS[i]["key"] == "reset"
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button in (1, 3):
            for i, rect in enumerate(self.rows):
                if rect.collidepoint(event.pos):
                    self.selected = i
                    opt = OPTIONS[i]
                    if opt["kind"] in ("choice", "slider"):
                        left_half = event.pos[0] < rect.right - S(160)
                        self.change(opt, -1 if (event.button == 3 or left_half) else 1)
                    else:
                        self.activate(opt)

    def _stop_editing(self, save):
        if save:
            name = self.editing.text.strip() or "Joueur"
            self.app.set_setting("player", name)
            self.app.audio.play("click")
        self.editing = None
        pygame.key.stop_text_input()

    def on_exit(self):
        if self.editing:
            self._stop_editing(save=True)

    def update(self, dt):
        super().update(dt)
        self.message_time = max(0.0, self.message_time - dt)
        for i in range(len(OPTIONS)):
            target = 1.0 if i == self.selected else 0.0
            self.hover[i] += (target - self.hover[i]) * min(1.0, dt * 14)
        for key in self.toggles:
            target = 1.0 if self.app.settings[key] else 0.0
            self.toggles[key] += (target - self.toggles[key]) * min(1.0, dt * 14)

    # --- Rendu ------------------------------------------------------------------------
    def draw(self, surf):
        super().draw(surf)
        theme = self.theme
        w, h = surf.get_size()
        self.draw_title(surf, "PARAMÈTRES", S(64))
        row_h, gap = S(40), S(5)
        width = min(w - S(60), S(720))
        top = S(118)
        self.rows = []
        for i, option in enumerate(OPTIONS):
            rect = pygame.Rect(0, 0, width, row_h)
            rect.midtop = (w // 2, top + i * (row_h + gap))
            self.rows.append(rect)
            appear = ui.ease_out_cubic((self.time - i * 0.03) / 0.35)
            if appear <= 0:
                continue
            self._draw_row(surf, rect.move(int((1 - appear) * S(60)), 0), option, i)
        if self.message_time > 0:
            alpha = int(255 * min(1.0, self.message_time))
            ui.draw_text(surf, self.message, S(18), theme["accent2"], (w // 2, h - S(60)), bold=True, alpha=alpha)
        hint = "Entrée valider     Échap annuler" if self.editing else \
            "↑ ↓  choisir     ← →  modifier     Entrée  valider     Échap  retour"
        self.draw_hint(surf, hint)

    def _draw_row(self, surf, rect, option, i):
        theme = self.theme
        hv = self.hover[i]
        fill = ui.lerp_color(theme["panel"], ui.darken(theme["accent"], 0.55), hv)
        border = (*ui.lerp_color(theme["panel"], theme["accent"], hv), 255)
        ui.draw_panel(surf, rect, fill, 220, S(12), border, S(2))
        label_color = theme["danger"] if option["key"] == "reset" else theme["text"]
        ui.draw_text(surf, option["label"], S(20), label_color, (rect.x + S(22), rect.centery), anchor="midleft",
                     bold=True)
        right = rect.right - S(22)
        kind, key = option["kind"], option["key"]
        value = self.app.settings.get(key)
        if kind == "text":
            if self.editing and i == self.selected:
                box = pygame.Rect(0, 0, S(260), rect.h - S(8))
                box.midright = (right + S(10), rect.centery)
                self.editing.draw(surf, box, theme, self.time)
            else:
                ui.draw_text(surf, value, S(20), theme["accent"], (right, rect.centery), anchor="midright", bold=True)
        elif kind == "choice":
            text = option["names"][value]
            ui.draw_text(surf, f"‹  {text}  ›", S(20), theme["accent"], (right, rect.centery), anchor="midright",
                         bold=True)
            if key == "theme":
                t = config.THEMES[value]
                for k, col in enumerate((t["snake_head"], t["snake_tail"], t["food"])):
                    pygame.draw.circle(surf, col, (right - S(170) - k * S(20), rect.centery), S(7))
        elif kind == "slider":
            seg_w, seg_gap = S(14), S(4)
            x = right - 10 * (seg_w + seg_gap) - S(40)
            for k in range(10):
                seg = pygame.Rect(x + k * (seg_w + seg_gap), rect.centery - S(9), seg_w, S(18))
                on = k < value
                pygame.draw.rect(surf, theme["accent"] if on else ui.darken(theme["panel"], 0.3), seg,
                                 border_radius=S(4))
            ui.draw_text(surf, str(value), S(20), theme["text"], (right, rect.centery), anchor="midright", bold=True)
        elif kind == "toggle":
            k = self.toggles[key]
            pill = pygame.Rect(0, 0, S(58), S(28))
            pill.midright = (right, rect.centery)
            pygame.draw.rect(surf, ui.lerp_color(ui.darken(theme["panel"], 0.35), theme["accent"], k), pill,
                             border_radius=S(14))
            knob_x = pill.x + S(14) + int((pill.w - S(28)) * k)
            pygame.draw.circle(surf, (250, 250, 255), (knob_x, pill.centery), S(11))
        elif key == "reset" and self.confirm_reset:
            ui.draw_text(surf, "Confirmer ?", S(18), theme["danger"], (right, rect.centery), anchor="midright", bold=True)
