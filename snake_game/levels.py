"""Définition des niveaux du mode Aventure (obstacles, portails, vitesse, objectif)."""
from dataclasses import dataclass, field

from .config import COLS, ROWS, RIGHT, UP


@dataclass
class Level:
    number: int
    name: str
    description: str
    wrap: bool                  # True : les bords sont traversables
    target: int                 # pommes à manger pour finir le niveau (0 = infini)
    speed: float                # cases par seconde
    obstacles: frozenset = frozenset()
    portals: list = field(default_factory=list)   # paires ((x1, y1), (x2, y2))
    spawn: tuple = (8, 10)
    direction: tuple = RIGHT

    def spawn_body(self):
        (x, y), (dx, dy) = self.spawn, self.direction
        return [(x - dx * i, y - dy * i) for i in range(3)]

    def portal_map(self):
        mapping = {}
        for a, b in self.portals:
            mapping[a], mapping[b] = b, a
        return mapping


# --- Petits outils pour dessiner des murs -------------------------------------------
def _h(cells, y, x1, x2, gaps=()):
    cells.update((x, y) for x in range(x1, x2 + 1) if x not in gaps)


def _v(cells, x, y1, y2, gaps=()):
    cells.update((x, y) for y in range(y1, y2 + 1) if y not in gaps)


def _block(cells, x, y, w, h):
    cells.update((x + i, y + j) for i in range(w) for j in range(h))


def _finalize(number, name, description, wrap, target, speed, cells=None, portals=(), spawn=(8, 10),
              direction=RIGHT):
    cells = set(cells or ())
    level = Level(number, name, description, wrap, target, speed, frozenset(), list(portals), spawn, direction)
    # On libère toujours le corps de départ et les 2 cases devant la tête.
    sx, sy = spawn
    dx, dy = direction
    safe = set(level.spawn_body()) | {(sx + dx, sy + dy), (sx + 2 * dx, sy + 2 * dy)}
    cells = {c for c in cells if c not in safe and 0 <= c[0] < COLS and 0 <= c[1] < ROWS}
    level.obstacles = frozenset(cells)
    return level


def _build_levels():
    levels = [_finalize(1, "Premiers pas", "Les bords sont ouverts : traversez-les !", True, 8, 7.0)]
    levels.append(_finalize(2, "L'enclos", "Attention, les bords sont désormais mortels.", False, 10, 7.5))

    c = set()
    for x, y in ((6, 4), (24, 4), (6, 14), (24, 14), (15, 2), (15, 16)):
        _block(c, x, y, 2, 2)
    levels.append(_finalize(3, "Les piliers", "Six piliers barrent la route.", False, 10, 8.0, c))

    c = set()
    _v(c, 16, 2, 17, gaps=(9, 10))
    _h(c, 10, 3, 28, gaps=range(14, 19))
    levels.append(_finalize(4, "Le carrefour", "Une grande croix au centre du monde.", True, 12, 8.5, c,
                            spawn=(6, 5)))

    c = set()
    _h(c, 5, 0, 25)
    _h(c, 10, 6, 31)
    _h(c, 15, 0, 25)
    levels.append(_finalize(5, "Les couloirs", "Serpentez entre les longs murs.", False, 12, 9.0, c,
                            spawn=(6, 2)))

    c = set()
    _h(c, 4, 4, 10); _v(c, 4, 4, 7)
    _h(c, 4, 21, 27); _v(c, 27, 4, 7)
    _h(c, 15, 4, 10); _v(c, 4, 12, 15)
    _h(c, 15, 21, 27); _v(c, 27, 12, 15)
    _block(c, 15, 8, 2, 4)
    levels.append(_finalize(6, "Les chambres", "Quatre coins, un cœur de pierre.", True, 14, 9.5, c,
                            spawn=(8, 2)))

    c = set()
    _v(c, 15, 0, 19)
    _v(c, 16, 0, 19)
    levels.append(_finalize(7, "Téléportation", "Le mur est infranchissable... sauf par les portails.",
                            False, 14, 10.0, c, portals=[((10, 4), (21, 15)), ((10, 15), (21, 4))],
                            spawn=(4, 10)))

    c = set()
    for x in range(2, COLS, 4):
        for y in (2, 6, 13, 17):
            c.add((x, y))
    _h(c, 9, 12, 19)
    levels.append(_finalize(8, "Le damier", "Une forêt de bornes à éviter.", True, 15, 10.5, c))

    c = set()
    _v(c, 5, 0, 6); _v(c, 5, 13, 19)
    _h(c, 4, 9, 20)
    _v(c, 12, 4, 8)
    _h(c, 15, 11, 22)
    _v(c, 20, 11, 15)
    _v(c, 26, 3, 9); _h(c, 9, 22, 26)
    _v(c, 26, 13, 19)
    levels.append(_finalize(9, "Le labyrinthe", "Murs, impasses et un portail salvateur.", False, 16, 11.0, c,
                            portals=[((2, 2), (29, 17))]))

    c = set()
    _h(c, 2, 3, 28, gaps=(15, 16)); _h(c, 17, 3, 28, gaps=(15, 16))
    _v(c, 3, 2, 17, gaps=(9, 10)); _v(c, 28, 2, 17, gaps=(9, 10))
    _h(c, 6, 9, 22, gaps=(20, 21)); _h(c, 13, 9, 22, gaps=(10, 11))
    _v(c, 9, 6, 13, gaps=(7, 8)); _v(c, 22, 6, 13, gaps=(11, 12))
    _block(c, 15, 9, 2, 2)
    levels.append(_finalize(10, "La forteresse", "L'épreuve finale : entrez dans la citadelle.", False, 18, 12.0,
                            c, spawn=(6, 10), direction=UP))
    return levels


LEVELS = _build_levels()
MAX_LEVEL = len(LEVELS)

# Le mode Classique : plateau vide, bords mortels, vitesse croissante.
CLASSIC = Level(0, "Classique", "Mangez sans fin, la vitesse augmente !", False, 0, 8.0)


def get_level(number):
    return LEVELS[number - 1]
