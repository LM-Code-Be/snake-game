"""Outils d'interface : échelle responsive, polices, couleurs, formes, boutons et menus."""
import math

import pygame

from .config import REFERENCE_SIZE

# --- Échelle responsive ----------------------------------------------------------
# Toute l'interface est pensée pour 1280x720 puis multipliée par ce facteur.
_scale = 1.0


def set_scale(width, height):
    global _scale
    _scale = max(0.5, min(width / REFERENCE_SIZE[0], height / REFERENCE_SIZE[1]))


def S(value):
    """Convertit une taille « de référence » en pixels réels."""
    return int(round(value * _scale))


# --- Maths & couleurs -------------------------------------------------------------
def clamp(v, lo=0.0, hi=1.0):
    return lo if v < lo else hi if v > hi else v


def lerp(a, b, t):
    return a + (b - a) * t


def lerp_color(c1, c2, t):
    t = clamp(t)
    return (int(c1[0] + (c2[0] - c1[0]) * t),
            int(c1[1] + (c2[1] - c1[1]) * t),
            int(c1[2] + (c2[2] - c1[2]) * t))


def lighten(color, amount):
    return lerp_color(color, (255, 255, 255), amount)


def darken(color, amount):
    return lerp_color(color, (0, 0, 0), amount)


def ease_out_cubic(t):
    t = clamp(t)
    return 1 - (1 - t) ** 3


def ease_in_out(t):
    t = clamp(t)
    return 3 * t * t - 2 * t * t * t


def ease_out_back(t):
    t = clamp(t)
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2


# --- Polices & texte ----------------------------------------------------------------
FONT_NAMES = "bahnschrift,segoeui,verdana,dejavusans,arial"
# Police de secours pour les symboles (flèches, étoiles) absents de la police principale.
SYMBOL_FONT_NAMES = "segoeuisymbol,seguisym,dejavusans,arial"
_fonts = {}
_text_cache = {}


def font(size, bold=False, symbols=False):
    key = (size, bold, symbols)
    if key not in _fonts:
        names = SYMBOL_FONT_NAMES if symbols else FONT_NAMES
        _fonts[key] = pygame.font.SysFont(names, max(8, size), bold=bold and not symbols)
    return _fonts[key]


def _is_symbol(ch):
    return ord(ch) >= 0x2190


def render_text(text, size, color, bold=False):
    key = (text, size, color, bold)
    surf = _text_cache.get(key)
    if surf is None:
        if len(_text_cache) > 800:
            _text_cache.clear()
        if not any(_is_symbol(ch) for ch in text):
            surf = font(size, bold).render(text, True, color)
        else:
            # Découpe en segments « texte » / « symboles » rendus chacun avec sa police.
            runs, current, sym = [], "", None
            for ch in text:
                if sym is not None and _is_symbol(ch) != sym:
                    runs.append((current, sym))
                    current = ""
                current += ch
                sym = _is_symbol(ch)
            runs.append((current, sym))
            parts = [font(size, bold, s).render(t, True, color) for t, s in runs]
            height = max(p.get_height() for p in parts)
            surf = pygame.Surface((sum(p.get_width() for p in parts), height), pygame.SRCALPHA)
            x = 0
            for p in parts:
                surf.blit(p, (x, (height - p.get_height()) // 2))
                x += p.get_width()
        _text_cache[key] = surf
    return surf


def draw_text(surf, text, size, color, pos, anchor="center", bold=False,
              shadow=True, alpha=255):
    """Dessine un texte (taille déjà en pixels) et renvoie son rectangle."""
    img = render_text(text, size, color, bold)
    rect = img.get_rect(**{anchor: (int(pos[0]), int(pos[1]))})
    if shadow:
        sh = render_text(text, size, (0, 0, 0), bold)
        sh.set_alpha(int(110 * alpha / 255))
        off = max(1, size // 18)
        surf.blit(sh, rect.move(off, off))
    img.set_alpha(alpha)
    surf.blit(img, rect)
    return rect


# --- Surfaces utilitaires -------------------------------------------------------------
def vertical_gradient(size, top, bottom):
    tiny = pygame.Surface((2, 2))
    tiny.fill(top)
    tiny.set_at((0, 1), bottom)
    tiny.set_at((1, 1), bottom)
    return pygame.transform.smoothscale(tiny, size)


_glow_cache = {}


def glow(radius, color):
    """Halo radial à blitter avec BLEND_ADD (rendu « néon »)."""
    radius = max(2, int(radius))
    key = (radius, color)
    surf = _glow_cache.get(key)
    if surf is None:
        if len(_glow_cache) > 400:
            _glow_cache.clear()
        surf = pygame.Surface((radius * 2, radius * 2))
        step = max(1, radius // 24)
        for r in range(radius, 0, -step):
            k = (1 - r / radius) ** 2
            pygame.draw.circle(surf, (int(color[0] * k), int(color[1] * k), int(color[2] * k)),
                               (radius, radius), r)
        _glow_cache[key] = surf
    return surf


def blit_glow(surf, center, radius, color):
    g = glow(radius, color)
    surf.blit(g, (center[0] - g.get_width() // 2, center[1] - g.get_height() // 2),
              special_flags=pygame.BLEND_ADD)


def draw_panel(surf, rect, color, alpha=230, radius=None, border=None, border_width=2):
    """Rectangle arrondi semi-transparent."""
    radius = S(16) if radius is None else radius
    panel = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(panel, (*color, alpha), panel.get_rect(), border_radius=radius)
    if border:
        pygame.draw.rect(panel, border, panel.get_rect(), max(1, border_width), border_radius=radius)
    surf.blit(panel, rect.topleft)


def dim_screen(surf, alpha=150, color=(0, 0, 0)):
    veil = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    veil.fill((*color, alpha))
    surf.blit(veil, (0, 0))


# --- Formes ----------------------------------------------------------------------------
def draw_heart(surf, center, size, color):
    cx, cy = center
    r = size * 0.28
    pygame.draw.circle(surf, color, (cx - size * 0.24, cy - size * 0.08), r)
    pygame.draw.circle(surf, color, (cx + size * 0.24, cy - size * 0.08), r)
    pygame.draw.polygon(surf, color, [(cx - size * 0.5, cy), (cx + size * 0.5, cy),
                                      (cx, cy + size * 0.48)])


def star_points(center, radius, inner=0.45):
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        r = radius if i % 2 == 0 else radius * inner
        pts.append((center[0] + math.cos(a) * r, center[1] + math.sin(a) * r))
    return pts


def draw_star(surf, center, radius, color, outline=None):
    pts = star_points(center, radius)
    pygame.draw.polygon(surf, color, pts)
    if outline:
        pygame.draw.polygon(surf, outline, pts, max(1, int(radius / 7)))


def draw_padlock(surf, center, size, color):
    cx, cy = center
    w, h = size * 0.7, size * 0.5
    body = pygame.Rect(0, 0, w, h)
    body.midtop = (cx, cy - size * 0.05)
    arc = pygame.Rect(0, 0, w * 0.7, size * 0.7)
    arc.midtop = (cx, cy - size * 0.42)
    pygame.draw.arc(surf, color, arc, 0, math.pi, max(2, int(size * 0.1)))
    pygame.draw.rect(surf, color, body, border_radius=max(2, int(size * 0.08)))


def draw_apple(surf, center, radius, color, leaf=(90, 210, 90)):
    cx, cy = center
    pygame.draw.circle(surf, darken(color, 0.25), (cx, cy), radius)
    pygame.draw.circle(surf, color, (cx - radius * 0.08, cy - radius * 0.1), radius * 0.88)
    pygame.draw.circle(surf, lighten(color, 0.55), (cx - radius * 0.38, cy - radius * 0.38),
                       max(1, radius * 0.2))
    pygame.draw.line(surf, (110, 70, 40), (cx, cy - radius * 0.8), (cx + radius * 0.15, cy - radius * 1.25),
                     max(2, int(radius * 0.16)))
    # Feuille : ellipse inclinée approximée par un polygone
    lx, ly, ang = cx + radius * 0.45, cy - radius * 1.05, -0.5
    pts = []
    for i in range(12):
        t = i / 12 * math.tau
        ex, ey = math.cos(t) * radius * 0.42, math.sin(t) * radius * 0.2
        pts.append((lx + ex * math.cos(ang) - ey * math.sin(ang), ly + ex * math.sin(ang) + ey * math.cos(ang)))
    pygame.draw.polygon(surf, leaf, pts)


def draw_powerup_icon(surf, kind, center, size, color, t=0.0):
    """Badge arrondi + pictogramme d'un bonus."""
    cx, cy = int(center[0]), int(center[1])
    rect = pygame.Rect(0, 0, int(size), int(size))
    rect.center = (cx, cy)
    pygame.draw.rect(surf, darken(color, 0.55), rect, border_radius=max(3, int(size * 0.28)))
    pygame.draw.rect(surf, color, rect, max(2, int(size * 0.08)), border_radius=max(3, int(size * 0.28)))
    white = (250, 250, 255)
    lw = max(2, int(size * 0.08))
    if kind == "slow":
        r = size * 0.27
        pygame.draw.circle(surf, white, (cx, cy), r, lw)
        a = t * 2.0
        pygame.draw.line(surf, white, (cx, cy), (cx, cy - r * 0.7), lw)
        pygame.draw.line(surf, white, (cx, cy), (cx + math.cos(a) * r * 0.6, cy + math.sin(a) * r * 0.6), lw)
    elif kind == "ghost":
        r = size * 0.22
        top = cy - size * 0.06
        pygame.draw.circle(surf, white, (cx, top), r)
        pygame.draw.rect(surf, white, (cx - r, top, r * 2, size * 0.24))
        for i in range(3):
            pygame.draw.circle(surf, white, (cx - r + r / 3 + i * r * 2 / 3, top + size * 0.24), r / 3)
        dark = darken(color, 0.6)
        pygame.draw.circle(surf, dark, (cx - r * 0.4, top), max(1, r * 0.22))
        pygame.draw.circle(surf, dark, (cx + r * 0.4, top), max(1, r * 0.22))
    elif kind == "shrink":
        s = size * 0.2
        pygame.draw.polygon(surf, white, [(cx - s * 1.6, cy - s), (cx - s * 0.3, cy), (cx - s * 1.6, cy + s)])
        pygame.draw.polygon(surf, white, [(cx + s * 1.6, cy - s), (cx + s * 0.3, cy), (cx + s * 1.6, cy + s)])
    elif kind == "double":
        draw_text(surf, "x2", max(8, int(size * 0.5)), white, (cx, cy), bold=True, shadow=False)


def make_icon():
    """Icône de fenêtre dessinée par le code (pas de fichier externe)."""
    icon = pygame.Surface((64, 64), pygame.SRCALPHA)
    pygame.draw.rect(icon, (20, 16, 42), icon.get_rect(), border_radius=14)
    pts = [(14, 46), (22, 46), (30, 46), (30, 38), (30, 30), (38, 30), (46, 30), (46, 22)]
    for i, p in enumerate(pts):
        col = lerp_color((150, 70, 255), (0, 255, 200), i / (len(pts) - 1))
        pygame.draw.circle(icon, col, p, 6)
    pygame.draw.circle(icon, (255, 70, 110), (46, 12), 5)
    return icon


# --- Boutons & menus ------------------------------------------------------------------------
class Button:
    def __init__(self, label, action, enabled=True, sub=None):
        self.label = label
        self.action = action
        self.enabled = enabled
        self.sub = sub
        self.rect = pygame.Rect(0, 0, 0, 0)
        self.hover = 0.0


class Menu:
    """Liste verticale de boutons pilotable au clavier et à la souris."""

    UP_KEYS = (pygame.K_UP, pygame.K_z, pygame.K_w)
    DOWN_KEYS = (pygame.K_DOWN, pygame.K_s)
    OK_KEYS = (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE)

    def __init__(self, app, buttons, width=380, height=56, gap=12):
        self.app = app
        self.buttons = buttons
        self.width, self.height, self.gap = width, height, gap
        self.selected = next((i for i, b in enumerate(buttons) if b.enabled), 0)
        self.age = 0.0

    def total_height(self):
        n = len(self.buttons)
        return n * S(self.height) + (n - 1) * S(self.gap)

    def layout(self, cx, top):
        w, h, g = S(self.width), S(self.height), S(self.gap)
        for i, b in enumerate(self.buttons):
            b.rect = pygame.Rect(0, 0, w, h)
            b.rect.midtop = (cx, top + i * (h + g))

    def move(self, step):
        n = len(self.buttons)
        i = self.selected
        for _ in range(n):
            i = (i + step) % n
            if self.buttons[i].enabled:
                break
        if i != self.selected:
            self.selected = i
            self.app.audio.play("hover")

    def activate(self):
        button = self.buttons[self.selected]
        if button.enabled:
            self.app.audio.play("click")
            button.action()

    def handle_event(self, e):
        if e.type == pygame.KEYDOWN:
            if e.key in self.UP_KEYS:
                self.move(-1)
            elif e.key in self.DOWN_KEYS:
                self.move(1)
            elif e.key in self.OK_KEYS:
                self.activate()
                return True
        elif e.type == pygame.MOUSEMOTION:
            for i, b in enumerate(self.buttons):
                if b.enabled and b.rect.collidepoint(e.pos) and i != self.selected:
                    self.selected = i
                    self.app.audio.play("hover")
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for i, b in enumerate(self.buttons):
                if b.enabled and b.rect.collidepoint(e.pos):
                    self.selected = i
                    self.activate()
                    return True
        return False

    def update(self, dt):
        self.age += dt
        for i, b in enumerate(self.buttons):
            target = 1.0 if i == self.selected else 0.0
            b.hover += (target - b.hover) * min(1.0, dt * 14)

    def draw(self, surf, theme):
        for i, b in enumerate(self.buttons):
            appear = ease_out_cubic((self.age - i * 0.06) / 0.45)
            if appear <= 0:
                continue
            rect = b.rect.inflate(int(S(14) * b.hover), int(S(4) * b.hover))
            rect.x += int((1 - appear) * -S(90))
            draw_button(surf, rect, b, theme, int(255 * appear))


def draw_button(surf, rect, button, theme, alpha=255):
    pad = S(14)
    layer = pygame.Surface((rect.w + pad * 2, rect.h + pad * 2), pygame.SRCALPHA)
    inner = pygame.Rect(pad, pad, rect.w, rect.h)
    radius = S(14)
    h = button.hover if button.enabled else 0.0
    accent = theme["accent"]
    if h > 0.02:
        for k in range(3):
            g = inner.inflate(S(4) * (k + 1) * 2, S(4) * (k + 1) * 2)
            pygame.draw.rect(layer, (*accent, int(28 * h / (k + 1))), g, border_radius=radius + S(4) * (k + 1))
    fill = lerp_color(theme["panel"], darken(accent, 0.45), h)
    pygame.draw.rect(layer, (*fill, 235), inner, border_radius=radius)
    border = lerp_color(darken(accent, 0.5), accent, h)
    pygame.draw.rect(layer, (*border, 255), inner, max(1, S(2)), border_radius=radius)
    if button.enabled:
        color = lerp_color(theme["text_dim"], theme["text"], 0.45 + 0.55 * h)
    else:
        color = darken(theme["text_dim"], 0.45)
    if h > 0.05:
        s = S(7)
        x = inner.x + S(18) - int((1 - h) * S(10))
        cy = inner.centery
        pygame.draw.polygon(layer, (*accent, int(255 * h)), [(x, cy - s), (x + s, cy), (x, cy + s)])
    size = S(24)
    if button.sub:
        draw_text(layer, button.label, size, color, (inner.centerx, inner.centery - S(8)), bold=True)
        draw_text(layer, button.sub, S(15), theme["text_dim"], (inner.centerx, inner.centery + S(14)),
                  shadow=False)
    else:
        draw_text(layer, button.label, size, color, inner.center, bold=True)
    layer.set_alpha(alpha)
    surf.blit(layer, (rect.x - pad, rect.y - pad))


class TextInput:
    """Champ de saisie simple (nom du joueur)."""

    def __init__(self, text="", max_len=14):
        self.text = text
        self.max_len = max_len
        self.fresh = True   # la première frappe remplace le texte proposé

    def handle_event(self, e):
        if e.type == pygame.TEXTINPUT:
            if self.fresh:
                self.text = ""
                self.fresh = False
            for ch in e.text:
                if ch.isprintable() and len(self.text) < self.max_len:
                    self.text += ch
        elif e.type == pygame.KEYDOWN:
            if e.key == pygame.K_BACKSPACE:
                self.fresh = False
                self.text = self.text[:-1]
            elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                return "submit"
        return None

    def draw(self, surf, rect, theme, time):
        draw_panel(surf, rect, darken(theme["panel"], 0.3), 240, S(12), theme["accent"], S(2))
        img = render_text(self.text, S(28), theme["text_dim"] if self.fresh else theme["text"], True)
        x = rect.centerx - img.get_width() // 2
        surf.blit(img, (x, rect.centery - img.get_height() // 2))
        if int(time * 2.2) % 2 == 0:
            cx = x + img.get_width() + S(4)
            pygame.draw.line(surf, theme["accent"], (cx, rect.centery - S(15)), (cx, rect.centery + S(15)), S(3))
