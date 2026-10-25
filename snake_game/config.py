"""Configuration globale : fenêtre, grille, vitesses, difficultés, thèmes et bonus."""
from pathlib import Path

# --- Chemins -----------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "snake.db"

# --- Fenêtre -----------------------------------------------------------------
TITLE = "Snake Néon"
VERSION = "1.0"
DEFAULT_WINDOW = (1280, 760)
REFERENCE_SIZE = (1280, 720)   # taille de référence pour l'échelle de l'interface
FPS = 120

# --- Grille de jeu -------------------------------------------------------------
COLS, ROWS = 32, 20

UP, DOWN, LEFT, RIGHT = (0, -1), (0, 1), (-1, 0), (1, 0)
OPPOSITE = {UP: DOWN, DOWN: UP, LEFT: RIGHT, RIGHT: LEFT}

# --- Règles --------------------------------------------------------------------
ADVENTURE_LIVES = 3
CLASSIC_LIVES = 1
COMBO_WINDOW = 2.5          # secondes pour enchaîner un combo
MAX_COMBO = 5
GOLDEN_CHANCE = 0.14        # probabilité d'une pomme dorée après chaque pomme
POWERUP_CHANCE = 0.20       # probabilité d'un bonus après chaque pomme
GOLDEN_TTL = 6.0
POWERUP_TTL = 8.0

DIFFICULTIES = {
    "facile":    {"label": "Facile",    "speed": 0.80, "score": 0.75},
    "normal":    {"label": "Normal",    "speed": 1.00, "score": 1.00},
    "difficile": {"label": "Difficile", "speed": 1.25, "score": 1.50},
}
DIFFICULTY_ORDER = ["facile", "normal", "difficile"]

# --- Bonus ---------------------------------------------------------------------
GOLD = (255, 205, 60)
POWERUPS = {
    "slow":   {"label": "Ralenti",  "color": (80, 170, 255),  "duration": 6.0,
               "desc": "Le temps ralentit pendant 6 s."},
    "ghost":  {"label": "Fantôme",  "color": (190, 120, 255), "duration": 6.0,
               "desc": "Traversez murs et queue pendant 6 s."},
    "double": {"label": "Score x2", "color": (255, 110, 200), "duration": 8.0,
               "desc": "Tous les points sont doublés pendant 8 s."},
    "shrink": {"label": "Rétrécir", "color": (70, 235, 210),  "duration": 0.0,
               "desc": "Le serpent perd 3 anneaux."},
}

# --- Thèmes de couleurs --------------------------------------------------------
THEMES = {
    "neon": {
        "label": "Néon",
        "bg_top": (12, 9, 30), "bg_bottom": (38, 12, 60),
        "board": (20, 16, 42), "board_alt": (25, 20, 50), "grid": (42, 36, 74),
        "panel": (32, 25, 64),
        "snake_head": (0, 255, 200), "snake_tail": (150, 70, 255),
        "accent": (0, 225, 255), "accent2": (255, 60, 180),
        "text": (240, 240, 255), "text_dim": (150, 148, 195),
        "obstacle": (92, 72, 158), "obstacle_light": (150, 128, 220),
        "food": (255, 70, 110), "danger": (255, 70, 95),
    },
    "ocean": {
        "label": "Océan",
        "bg_top": (4, 16, 34), "bg_bottom": (6, 44, 76),
        "board": (8, 28, 52), "board_alt": (10, 34, 60), "grid": (26, 62, 94),
        "panel": (12, 42, 70),
        "snake_head": (100, 245, 255), "snake_tail": (20, 105, 225),
        "accent": (60, 205, 255), "accent2": (255, 200, 80),
        "text": (230, 245, 255), "text_dim": (130, 170, 205),
        "obstacle": (30, 82, 124), "obstacle_light": (64, 136, 186),
        "food": (255, 120, 90), "danger": (255, 95, 95),
    },
    "foret": {
        "label": "Forêt",
        "bg_top": (7, 20, 12), "bg_bottom": (20, 46, 26),
        "board": (14, 32, 20), "board_alt": (17, 38, 24), "grid": (34, 64, 42),
        "panel": (22, 48, 30),
        "snake_head": (195, 255, 90), "snake_tail": (30, 160, 85),
        "accent": (150, 240, 110), "accent2": (255, 210, 90),
        "text": (235, 250, 230), "text_dim": (150, 190, 150),
        "obstacle": (86, 72, 50), "obstacle_light": (138, 118, 82),
        "food": (255, 80, 70), "danger": (255, 95, 70),
    },
    "crepuscule": {
        "label": "Crépuscule",
        "bg_top": (28, 8, 20), "bg_bottom": (74, 24, 42),
        "board": (40, 14, 28), "board_alt": (47, 18, 33), "grid": (76, 36, 56),
        "panel": (58, 20, 38),
        "snake_head": (255, 215, 95), "snake_tail": (255, 70, 125),
        "accent": (255, 150, 80), "accent2": (140, 200, 255),
        "text": (255, 240, 235), "text_dim": (205, 150, 162),
        "obstacle": (104, 42, 72), "obstacle_light": (165, 74, 114),
        "food": (120, 255, 170), "danger": (255, 85, 85),
    },
}
THEME_ORDER = ["neon", "ocean", "foret", "crepuscule"]
for _key, _theme in THEMES.items():
    _theme["name"] = _key

# --- Paramètres par défaut (persistés en base) ---------------------------------
DEFAULT_SETTINGS = {
    "player": "Joueur",
    "difficulty": "normal",
    "theme": "neon",
    "music_volume": 5,
    "sfx_volume": 8,
    "show_grid": True,
    "screen_shake": True,
    "fullscreen": False,
    "show_fps": False,
}
