"""Classements, historique des parties et statistiques globales (lus depuis SQLite)."""
from datetime import datetime

import pygame

from .. import config, ui
from ..config import GOLD
from ..levels import MAX_LEVEL
from ..ui import S
from .base import Scene
from .gameover import format_duration

TABS = ["Aventure", "Classique", "Historique", "Statistiques"]
MEDALS = [GOLD, (205, 215, 230), (215, 140, 80)]


def format_date(iso):
    try:
        return datetime.fromisoformat(iso).strftime("%d/%m/%y %H:%M")
    except ValueError:
        return iso


class ScoresScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        db = app.db
        self.data = {
            "Aventure": db.top_scores("aventure"),
            "Classique": db.top_scores("classique"),
            "Historique": db.recent_games(10),
        }
        self.stats = db.stats()
        self.tab = 0
        self.tab_time = 0.0
        self.tab_rects = []
        self.tab_x = 0.0   # position animée du soulignement

    def set_tab(self, index):
        index %= len(TABS)
        if index != self.tab:
            self.tab = index
            self.tab_time = 0.0
            self.app.audio.play("hover")

    def handle_event(self, event):
        if self.is_back(event):
            self.go_menu()
        elif event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_LEFT, pygame.K_q, pygame.K_a):
                self.set_tab(self.tab - 1)
            elif event.key in (pygame.K_RIGHT, pygame.K_d, pygame.K_TAB):
                self.set_tab(self.tab + 1)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, rect in enumerate(self.tab_rects):
                if rect.collidepoint(event.pos):
                    self.set_tab(i)

    def update(self, dt):
        super().update(dt)
        self.tab_time += dt

    def draw(self, surf):
        super().draw(surf)
        theme = self.theme
        w, h = surf.get_size()
        self.draw_title(surf, "SCORES", S(64))

        # Onglets
        tab_w, tab_h = S(190), S(44)
        total = len(TABS) * tab_w
        x0 = w // 2 - total // 2
        self.tab_rects = [pygame.Rect(x0 + i * tab_w, S(110), tab_w, tab_h) for i in range(len(TABS))]
        target = self.tab_rects[self.tab].x
        self.tab_x += (target - self.tab_x) * 0.25 if self.tab_x else target
        for i, rect in enumerate(self.tab_rects):
            color = theme["text"] if i == self.tab else theme["text_dim"]
            ui.draw_text(surf, TABS[i], S(21), color, rect.center, bold=True)
        bar = pygame.Rect(int(self.tab_x) + S(30), S(110) + tab_h, tab_w - S(60), S(4))
        pygame.draw.rect(surf, theme["accent"], bar, border_radius=S(2))

        panel = pygame.Rect(0, 0, min(w - S(60), S(900)), h - S(250))
        panel.midtop = (w // 2, S(175))
        ui.draw_panel(surf, panel, theme["panel"], 200, S(20))
        name = TABS[self.tab]
        if name in ("Aventure", "Classique"):
            self._draw_ranking(surf, panel, self.data[name], name == "Aventure")
        elif name == "Historique":
            self._draw_history(surf, panel, self.data[name])
        else:
            self._draw_stats(surf, panel)
        self.draw_hint(surf, "← →  changer d'onglet     Échap  retour")

    def _row_alpha(self, i):
        return int(255 * ui.ease_out_cubic((self.tab_time - i * 0.04) / 0.3))

    def _columns(self, panel, spec):
        """spec : liste de (titre, fraction de largeur, ancre)."""
        x = panel.x + S(30)
        width = panel.w - S(60)
        cols = []
        for title, frac, anchor in spec:
            cw = width * frac
            px = x if anchor == "midleft" else x + cw / 2 if anchor == "center" else x + cw
            cols.append((title, px, anchor))
            x += cw
        return cols

    def _draw_table(self, surf, panel, cols, rows, empty_text, medal=False):
        theme = self.theme
        head_y = panel.y + S(32)
        for title, x, anchor in cols:
            ui.draw_text(surf, title, S(15), theme["text_dim"], (x, head_y), anchor=anchor, bold=True)
        if not rows:
            ui.draw_text(surf, empty_text, S(22), theme["text_dim"], panel.center)
            return
        row_h = min(S(44), (panel.h - S(70)) // max(1, len(rows)))
        for i, values in enumerate(rows):
            alpha = self._row_alpha(i)
            if alpha <= 0:
                continue
            y = head_y + S(30) + i * row_h + row_h // 2
            strip = pygame.Rect(panel.x + S(14), y - row_h // 2 + S(2), panel.w - S(28), row_h - S(4))
            if i % 2 == 0:
                ui.draw_panel(surf, strip, ui.lighten(theme["panel"], 0.06), int(alpha * 0.8), S(10))
            for c, ((_, x, anchor), value) in enumerate(zip(cols, values)):
                if medal and c == 0 and i < 3:
                    pygame.draw.circle(surf, MEDALS[i], (x + S(12), y), S(13))
                    ui.draw_text(surf, value, S(16), (30, 25, 40), (x + S(12), y), bold=True, shadow=False)
                    continue
                color = theme["text"] if c != 2 else theme["accent"]
                ui.draw_text(surf, value, S(18), color, (x, y), anchor=anchor, bold=c == 2, alpha=alpha)

    def _draw_ranking(self, surf, panel, rows, adventure):
        cols = self._columns(panel, [("#", 0.08, "midleft"), ("JOUEUR", 0.3, "midleft"), ("SCORE", 0.16, "midright"),
                                     ("NIVEAU" if adventure else "POMMES", 0.16, "center"),
                                     ("DIFFICULTÉ", 0.14, "center"), ("DATE", 0.16, "midright")])
        data = []
        for i, r in enumerate(rows):
            detail = (f"{r['level']}{' ★' if r['victory'] else ''}") if adventure else str(r["apples"])
            data.append([str(i + 1), r["player"], str(r["score"]), detail,
                         config.DIFFICULTIES.get(r["difficulty"], {"label": "?"})["label"],
                         format_date(r["played_at"])])
        self._draw_table(surf, panel, cols, data, "Aucun score pour l'instant. À vous de jouer !", medal=True)

    def _draw_history(self, surf, panel, rows):
        cols = self._columns(panel, [("DATE", 0.2, "midleft"), ("JOUEUR", 0.24, "midleft"), ("SCORE", 0.14, "midright"),
                                     ("MODE", 0.16, "center"), ("DURÉE", 0.12, "center"), ("RÉSULTAT", 0.14, "midright")])
        data = []
        for r in rows:
            mode = "Aventure" if r["mode"] == "aventure" else "Classique"
            if r["victory"]:
                result = "Victoire"
            elif r["mode"] == "aventure":
                result = f"Niveau {r['level']}"
            else:
                result = f"{r['apples']} pommes"
            data.append([format_date(r["played_at"]), r["player"], str(r["score"]), mode,
                         format_duration(r["duration"]), result])
        self._draw_table(surf, panel, cols, data, "L'historique est vide.")

    def _draw_stats(self, surf, panel):
        theme = self.theme
        s = self.stats
        hours, rest = divmod(int(s["duration"]), 3600)
        items = [
            ("Parties jouées", str(s["games"])), ("Meilleur score", str(s["best"])),
            ("Score moyen", str(int(s["average"]))), ("Pommes mangées", str(s["apples"])),
            ("Temps de jeu", f"{hours} h {rest // 60:02d}" if hours else format_duration(s["duration"])),
            ("Serpent le plus long", str(s["longest"])), ("Meilleur combo", f"x{s['combo']}"),
            ("Niveaux terminés", f"{s['levels_done']} / {MAX_LEVEL}"),
            ("Étoiles", f"{s['stars']} / {MAX_LEVEL * 3}"),
        ]
        cols = 3
        gap = S(16)
        cw = (panel.w - S(40) - gap * (cols - 1)) // cols
        ch = min(S(100), (panel.h - S(40) - gap * 2) // 3)
        for i, (label, value) in enumerate(items):
            alpha = self._row_alpha(i)
            if alpha <= 0:
                continue
            col, row = i % cols, i // cols
            rect = pygame.Rect(panel.x + S(20) + col * (cw + gap), panel.y + S(20) + row * (ch + gap), cw, ch)
            ui.draw_panel(surf, rect, ui.lighten(theme["panel"], 0.06), int(alpha * 0.9), S(14))
            ui.draw_text(surf, value, S(32), theme["accent"] if i % 2 == 0 else theme["accent2"],
                         (rect.centerx, rect.centery - S(10)), bold=True, alpha=alpha)
            ui.draw_text(surf, label, S(15), theme["text_dim"], (rect.centerx, rect.centery + S(24)), alpha=alpha)
