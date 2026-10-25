"""Entités du jeu : le serpent et les objets à ramasser."""
from collections import deque

from .config import OPPOSITE


class Snake:
    def __init__(self, body, direction):
        self.body = deque(body)          # la tête est en position 0
        self.prev_body = list(body)      # positions au pas précédent (pour l'interpolation)
        self.direction = direction
        self.queue = deque()             # virages mémorisés (permet d'enchaîner vite)
        self.grow_pending = 0

    @property
    def head(self):
        return self.body[0]

    def queue_direction(self, direction):
        last = self.queue[-1] if self.queue else self.direction
        if direction != last and direction != OPPOSITE[last] and len(self.queue) < 3:
            self.queue.append(direction)

    def next_direction(self):
        if self.queue:
            self.direction = self.queue.popleft()
        return self.direction

    def blocking_cells(self):
        """Cases mortelles pour la tête : la queue se libère si le serpent ne grandit pas."""
        cells = list(self.body)
        if self.grow_pending == 0:
            cells.pop()
        return set(cells)

    def move_to(self, cell):
        self.prev_body = list(self.body)
        self.body.appendleft(cell)
        if self.grow_pending > 0:
            self.grow_pending -= 1
        else:
            self.body.pop()

    def shrink(self, amount, minimum=3):
        for _ in range(amount):
            if len(self.body) <= minimum:
                break
            self.body.pop()
        self.prev_body = self.prev_body[:len(self.body)]


class Item:
    """Objet posé sur le plateau : pomme, pomme dorée ou bonus."""

    def __init__(self, kind, pos, born, ttl=None):
        self.kind = kind      # "apple", "golden" ou une clé de config.POWERUPS
        self.pos = pos
        self.born = born
        self.ttl = ttl        # durée de vie restante (None = permanent)
        self.total = ttl
