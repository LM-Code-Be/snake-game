"""Écran « Comment jouer » : commandes, objets et règles."""
import pygame

from .. import ui
from ..config import GOLD, POWERUPS
from ..ui import S
from .base import Scene

CONTROLS = [
    ("Flèches / ZQSD / WASD", "Diriger le serpent"),
    ("Échap / P", "Pause"),
    ("F11 / Alt + Entrée", "Plein écran"),
    ("Entrée", "Passer l'introduction"),
]

RULES = [
    "Mangez les pommes pour grandir et marquer des points.",
    "Enchaînez-les rapidement pour monter le combo (jusqu'à x5).",
    "Aventure : atteignez l'objectif de pommes pour finir le niveau.",
    "Vous avez 3 vies ; ne perdez aucune vie pour obtenir 3 étoiles.",
    "Bords rouges = mortels ; bords bleutés = traversables.",
    "Les portails vous téléportent vers leur jumeau.",
]


class HelpScene(Scene):
    def handle_event(self, event):
        if self.is_back(event) or (event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN):
            self.go_menu()

    def draw(self, surf):
        super().draw(surf)
        theme = self.theme
        w, h = surf.get_size()
        self.draw_title(surf, "COMMENT JOUER", S(64))
        col_w = min(S(560), (w - S(80)) // 2)
        panel_h = min(h - S(190), S(430))
        top = max(S(115), (h - panel_h) // 2 + S(20))
        left = pygame.Rect(w // 2 - col_w - S(12), top, col_w, panel_h)
        right = pygame.Rect(w // 2 + S(12), top, col_w, panel_h)
        for rect in (left, right):
            ui.draw_panel(surf, rect, theme["panel"], 210, S(20))

        # Colonne gauche : commandes + règles
        y = left.y + S(32)
        ui.draw_text(surf, "COMMANDES", S(18), theme["accent"], (left.x + S(24), y), anchor="midleft", bold=True)
        y += S(36)
        for key, action in CONTROLS:
            ui.draw_text(surf, key, S(17), theme["text"], (left.x + S(24), y), anchor="midleft", bold=True)
            ui.draw_text(surf, action, S(17), theme["text_dim"], (left.right - S(24), y), anchor="midright")
            y += S(30)
        y += S(16)
        ui.draw_text(surf, "RÈGLES", S(18), theme["accent"], (left.x + S(24), y), anchor="midleft", bold=True)
        y += S(32)
        for rule in RULES:
            pygame.draw.circle(surf, theme["accent2"], (left.x + S(30), y), S(4))
            ui.draw_text(surf, rule, S(15), theme["text"], (left.x + S(44), y), anchor="midleft")
            y += S(27)

        # Colonne droite : objets
        y = right.y + S(32)
        ui.draw_text(surf, "OBJETS", S(18), theme["accent"], (right.x + S(24), y), anchor="midleft", bold=True)
        y += S(46)
        items = [("apple", "Pomme", "+10 pts (x niveau x combo), +1 anneau", theme["food"]),
                 ("golden", "Pomme dorée", "+50 pts, disparaît après 6 s", GOLD)]
        items += [(k, v["label"], v["desc"], v["color"]) for k, v in POWERUPS.items()]
        for kind, name, desc, color in items:
            cx = right.x + S(46)
            ui.blit_glow(surf, (cx, y), S(34), ui.darken(color, 0.55))
            if kind in ("apple", "golden"):
                ui.draw_apple(surf, (cx, y + S(2)), S(14), color)
            else:
                ui.draw_powerup_icon(surf, kind, (cx, y), S(34), color, self.time)
            ui.draw_text(surf, name, S(18), theme["text"], (cx + S(36), y - S(10)), anchor="midleft", bold=True)
            ui.draw_text(surf, desc, S(15), theme["text_dim"], (cx + S(36), y + S(12)), anchor="midleft")
            y += S(58)
        self.draw_hint(surf, "Échap  retour")
