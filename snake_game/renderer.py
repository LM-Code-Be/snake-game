"""Rendu du plateau : cases, obstacles, portails, objets et serpent (avec interpolation)."""
import math

import pygame

from . import ui
from .config import COLS, GOLD, POWERUPS, ROWS
from .ui import S


class BoardRenderer:
    def __init__(self):
        self.cell = 20
        self.rect = pygame.Rect(0, 0, COLS * 20, ROWS * 20)
        self._static = None
        self._static_key = None

    # --- Mise en page responsive -------------------------------------------------
    def layout(self, area):
        """Calcule la taille d'une case pour que la grille tienne dans `area`."""
        self.cell = max(6, min(area.w // COLS, area.h // ROWS))
        self.rect = pygame.Rect(0, 0, self.cell * COLS, self.cell * ROWS)
        self.rect.center = area.center

    def center(self, gx, gy):
        """Centre d'une case, en pixels, relatif au coin du plateau."""
        return (gx + 0.5) * self.cell, (gy + 0.5) * self.cell

    # --- Couche statique (mise en cache) -----------------------------------------------
    def _build_static(self, level, theme, show_grid):
        c = self.cell
        surf = pygame.Surface(self.rect.size)
        surf.fill(theme["board"])
        for y in range(ROWS):
            for x in range(COLS):
                if (x + y) % 2:
                    pygame.draw.rect(surf, theme["board_alt"], (x * c, y * c, c, c))
        if show_grid:
            for x in range(1, COLS):
                pygame.draw.line(surf, theme["grid"], (x * c, 0), (x * c, self.rect.h))
            for y in range(1, ROWS):
                pygame.draw.line(surf, theme["grid"], (0, y * c), (self.rect.w, y * c))
        radius = max(2, c // 4)
        shadow = ui.darken(theme["board"], 0.55)
        for x, y in level.obstacles:
            pygame.draw.rect(surf, shadow, (x * c + 1, y * c + c * 0.15, c - 2, c - 1), border_radius=radius)
        for x, y in level.obstacles:
            r = pygame.Rect(x * c + 1, y * c + 1, c - 2, c - 2)
            pygame.draw.rect(surf, theme["obstacle"], r, border_radius=radius)
            top = pygame.Rect(r.x + c * 0.16, r.y + c * 0.12, r.w - c * 0.32, max(2, c * 0.2))
            pygame.draw.rect(surf, theme["obstacle_light"], top, border_radius=radius)
        return surf

    def draw_board(self, surf, level, theme, show_grid, time, offset=(0, 0)):
        key = (self.cell, level.number, level.obstacles, theme["name"], show_grid)
        if key != self._static_key:
            self._static_key = key
            self._static = self._build_static(level, theme, show_grid)
        ox, oy = self.rect.x + offset[0], self.rect.y + offset[1]
        frame = pygame.Rect(ox, oy, self.rect.w, self.rect.h).inflate(S(18), S(18))
        pygame.draw.rect(surf, ui.darken(theme["panel"], 0.25), frame.move(0, S(6)), border_radius=S(16))
        pygame.draw.rect(surf, theme["panel"], frame, border_radius=S(16))
        surf.blit(self._static, (ox, oy))
        pulse = 0.5 + 0.5 * math.sin(time * 3)
        if level.wrap:
            color = ui.lerp_color(theme["panel"], theme["accent"], 0.35 + 0.25 * pulse)
            pygame.draw.rect(surf, color, frame, max(1, S(2)), border_radius=S(16))
        else:
            color = ui.lerp_color(theme["panel"], theme["danger"], 0.55 + 0.35 * pulse)
            pygame.draw.rect(surf, color, frame, max(2, S(3)), border_radius=S(16))

    # --- Objets ---------------------------------------------------------------------
    def draw_portals(self, surf, level, theme, time, offset):
        ox, oy = self.rect.x + offset[0], self.rect.y + offset[1]
        colors = (theme["accent"], theme["accent2"])
        for idx, pair in enumerate(level.portals):
            color = colors[idx % 2]
            for gx, gy in pair:
                cx, cy = self.center(gx, gy)
                cx, cy = cx + ox, cy + oy
                r = self.cell * 0.48
                ui.blit_glow(surf, (cx, cy), r * 2.2, ui.darken(color, 0.4))
                pygame.draw.circle(surf, ui.darken(color, 0.75), (cx, cy), r)
                for k in range(3):
                    a = time * (3 + k) + k * 2.1
                    rect = pygame.Rect(0, 0, r * 2 * (1 - k * 0.25), r * 2 * (1 - k * 0.25))
                    rect.center = (cx, cy)
                    pygame.draw.arc(surf, ui.lighten(color, k * 0.2), rect, a, a + 3.6, max(2, int(self.cell * 0.08)))

    def draw_item(self, surf, item, theme, time, offset):
        ox, oy = self.rect.x + offset[0], self.rect.y + offset[1]
        cx, cy = self.center(*item.pos)
        cx, cy = cx + ox, cy + oy
        age = time - item.born
        scale = ui.ease_out_back(age / 0.35)
        if scale <= 0:
            return
        if item.ttl is not None and item.ttl < 2.0 and int(time * 10) % 2 == 0:
            return  # clignote avant de disparaître
        c = self.cell
        if item.kind in ("apple", "golden"):
            color = theme["food"] if item.kind == "apple" else GOLD
            bob = math.sin(time * 4 + item.pos[0]) * c * 0.04
            r = c * 0.36 * scale * (1 + 0.06 * math.sin(time * 6))
            ui.blit_glow(surf, (cx, cy), c * 1.1 * scale, ui.darken(color, 0.55))
            ui.draw_apple(surf, (cx, cy + bob), r, color)
            if item.kind == "golden" and item.total:
                rect = pygame.Rect(0, 0, c * 1.25, c * 1.25)
                rect.center = (cx, cy)
                frac = item.ttl / item.total
                pygame.draw.arc(surf, GOLD, rect, math.pi / 2, math.pi / 2 + math.tau * frac, max(2, S(2)))
        else:
            color = POWERUPS[item.kind]["color"]
            bob = math.sin(time * 3.5) * c * 0.08
            ui.blit_glow(surf, (cx, cy), c * 1.2 * scale, ui.darken(color, 0.45))
            ui.draw_powerup_icon(surf, item.kind, (cx, cy + bob), c * 0.86 * scale, color, time)

    # --- Serpent ---------------------------------------------------------------------
    def snake_points(self, snake, t):
        """Positions (pixels) de chaque anneau, interpolées entre deux pas de jeu."""
        pts = []
        prev = snake.prev_body
        for i, (x, y) in enumerate(snake.body):
            px, py = prev[min(i, len(prev) - 1)]
            if abs(x - px) + abs(y - py) == 1:
                gx, gy = px + (x - px) * t, py + (y - py) * t
            else:
                gx, gy = x, y      # traversée d'un bord ou d'un portail : pas d'interpolation
            pts.append(self.center(gx, gy))
        return pts

    def draw_snake(self, surf, snake, t, theme, time, offset, ghost=False, popped=0, flash=0.0, alive=True):
        ox, oy = self.rect.x + offset[0], self.rect.y + offset[1]
        c = self.cell
        pts = [(x + ox, y + oy) for x, y in self.snake_points(snake, t)]
        n = len(pts)
        if popped >= n:
            return
        head_col, tail_col = theme["snake_head"], theme["snake_tail"]

        def radius(i):
            k = i / max(1, n - 1)
            return c * (0.44 - 0.16 * max(0.0, (k - 0.55) / 0.45))

        def color(i):
            col = ui.lerp_color(head_col, tail_col, i / max(1, n - 1))
            if i % 2:
                col = ui.darken(col, 0.1)
            if ghost:
                col = ui.lerp_color(col, theme["board"], 0.55 + 0.15 * math.sin(time * 12))
            if flash > 0:
                col = ui.lerp_color(col, (255, 255, 255), flash)
            return col

        def close(a, b):
            return abs(a[0] - b[0]) + abs(a[1] - b[1]) <= c * 1.2

        # Ombre portée
        shadow = ui.darken(theme["board"], 0.6)
        sh = c * 0.14
        for i in range(n - 1, popped - 1, -1):
            pygame.draw.circle(surf, shadow, (pts[i][0] + sh, pts[i][1] + sh), radius(i))

        # Corps, de la queue vers la tête, avec un anneau intermédiaire pour lisser
        for i in range(n - 1, popped - 1, -1):
            r = radius(i)
            col = color(i)
            if i > popped and close(pts[i], pts[i - 1]):
                mid = ((pts[i][0] + pts[i - 1][0]) / 2, (pts[i][1] + pts[i - 1][1]) / 2)
                pygame.draw.circle(surf, col, mid, (r + radius(i - 1)) / 2)
            pygame.draw.circle(surf, col, pts[i], r)
            pygame.draw.circle(surf, ui.lighten(col, 0.3), (pts[i][0] - r * 0.25, pts[i][1] - r * 0.3), r * 0.35)

        if popped > 0:
            return

        # Tête : un peu plus grosse, avec yeux et langue
        hx, hy = pts[0]
        r = c * 0.5
        col = color(0)
        if not ghost:
            ui.blit_glow(surf, (hx, hy), r * 2.4, ui.darken(head_col, 0.75))
        pygame.draw.circle(surf, col, (hx, hy), r)
        pygame.draw.circle(surf, ui.lighten(col, 0.3), (hx - r * 0.25, hy - r * 0.3), r * 0.35)
        dx, dy = snake.direction
        px, py = -dy, dx
        if alive and (time % 3.2) < 0.25:
            tx, ty = hx + dx * r * 0.9, hy + dy * r * 0.9
            ex, ey = tx + dx * r * 0.6, ty + dy * r * 0.6
            lw = max(1, int(c * 0.07))
            pygame.draw.line(surf, (255, 60, 90), (tx, ty), (ex, ey), lw)
            pygame.draw.line(surf, (255, 60, 90), (ex, ey), (ex + (dx + px) * r * 0.25, ey + (dy + py) * r * 0.25), lw)
            pygame.draw.line(surf, (255, 60, 90), (ex, ey), (ex + (dx - px) * r * 0.25, ey + (dy - py) * r * 0.25), lw)
        blinking = (time % 4.0) > 3.85
        for side in (-1, 1):
            ex, ey = hx + dx * r * 0.25 + px * r * 0.45 * side, hy + dy * r * 0.25 + py * r * 0.45 * side
            if not alive:
                s = r * 0.22
                pygame.draw.line(surf, (30, 20, 40), (ex - s, ey - s), (ex + s, ey + s), max(1, int(c * 0.08)))
                pygame.draw.line(surf, (30, 20, 40), (ex - s, ey + s), (ex + s, ey - s), max(1, int(c * 0.08)))
            elif blinking:
                pygame.draw.line(surf, (30, 20, 40), (ex - px * r * 0.25, ey - py * r * 0.25),
                                 (ex + px * r * 0.25, ey + py * r * 0.25), max(1, int(c * 0.08)))
            else:
                pygame.draw.circle(surf, (250, 250, 255), (ex, ey), r * 0.3)
                pygame.draw.circle(surf, (25, 20, 40), (ex + dx * r * 0.1, ey + dy * r * 0.1), r * 0.16)


def draw_level_preview(surf, level, rect, theme):
    """Miniature d'un niveau (écran de sélection)."""
    cell = max(1, min(rect.w // COLS, rect.h // ROWS))
    board = pygame.Rect(0, 0, cell * COLS, cell * ROWS)
    board.center = rect.center
    pygame.draw.rect(surf, theme["board"], board)
    for x, y in level.obstacles:
        pygame.draw.rect(surf, theme["obstacle_light"], (board.x + x * cell, board.y + y * cell, cell, cell))
    for idx, pair in enumerate(level.portals):
        color = theme["accent"] if idx % 2 == 0 else theme["accent2"]
        for x, y in pair:
            pygame.draw.circle(surf, color, (board.x + (x + 0.5) * cell, board.y + (y + 0.5) * cell), cell)
    for i, (x, y) in enumerate(level.spawn_body()):
        col = theme["snake_head"] if i == 0 else theme["snake_tail"]
        pygame.draw.rect(surf, col, (board.x + x * cell, board.y + y * cell, cell, cell))
    border = theme["accent"] if level.wrap else theme["danger"]
    pygame.draw.rect(surf, border, board.inflate(2, 2), 1)
