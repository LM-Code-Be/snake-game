"""Scène de jeu : logique du serpent, niveaux, bonus, HUD, pause et sauvegarde."""
import math
import random

import pygame

from .. import config, ui
from ..config import COLS, ROWS, DOWN, LEFT, RIGHT, UP, POWERUPS, GOLD
from ..effects import FloatingTexts, ParticleSystem, ScreenShake
from ..entities import Item, Snake
from ..levels import CLASSIC, MAX_LEVEL, get_level
from ..renderer import BoardRenderer
from ..ui import S, Button, Menu
from .base import Scene

KEY_DIRECTIONS = {
    pygame.K_UP: UP, pygame.K_z: UP, pygame.K_w: UP,
    pygame.K_DOWN: DOWN, pygame.K_s: DOWN,
    pygame.K_LEFT: LEFT, pygame.K_q: LEFT, pygame.K_a: LEFT,
    pygame.K_RIGHT: RIGHT, pygame.K_d: RIGHT,
}

CARD_TIME = 1.7       # durée de la carte « Niveau X »
COUNT_TIME = 1.8      # compte à rebours 3-2-1
DEATH_TIME = 1.6
COMPLETE_TIME = 3.2


class GameScene(Scene):
    def __init__(self, app, mode="aventure", level=1, saved=None):
        super().__init__(app)
        self.mode = saved["mode"] if saved else mode
        self.renderer = BoardRenderer()
        self.particles = ParticleSystem()
        self.texts = FloatingTexts()
        self.shake = ScreenShake()
        self.difficulty = config.DIFFICULTIES[app.settings["difficulty"]]
        self.record = app.db.best_score(self.mode)

        self.score = 0
        self.shown_score = 0.0
        self.lives = config.ADVENTURE_LIVES if self.mode == "aventure" else config.CLASSIC_LIVES
        self.level_num = level if self.mode == "aventure" else 0
        self.apples_total = 0
        self.max_length = 3
        self.max_combo = 0
        self.elapsed = 0.0
        self.finished = False
        self.go_timer = 0.0
        self.pop_timer = 0.0
        self.paused_from = "playing"
        self.stars = 0
        self._star_sounds = 0
        self._last_tick = None

        self.load_level(self.level_num)
        if saved:
            self._restore(saved)
        elif self.mode == "aventure":
            self.autosave()

        self.pause_menu = Menu(app, [
            Button("Reprendre", self.resume),
            Button("Recommencer", self.restart),
            Button("Sauvegarder et quitter", self.save_and_quit),
            Button("Abandonner la partie", self.abandon),
        ], width=380, height=54, gap=10)
        self.layout_board()

    # ==== Mise en place ==========================================================
    def load_level(self, number, show_card=True):
        self.level = get_level(number) if self.mode == "aventure" else CLASSIC
        self.portals = self.level.portal_map()
        self.apples_level = 0
        self.level_score = 0
        self.lives_lost_level = 0
        self.items = []
        self.effects = {}
        self.combo = 0
        self.since_eat = 99.0
        self.reset_snake()
        self.spawn_item("apple")
        self.set_state("intro")
        self.show_card = show_card

    def reset_snake(self):
        self.snake = Snake(self.level.spawn_body(), self.level.direction)
        self.accumulator = 0.0
        self.move_t = 0.0
        self.popped = 0

    def set_state(self, state):
        self.state = state
        self.state_time = 0.0

    def layout_board(self):
        w, h = self.app.screen.get_size()
        hud = S(86)
        margin = S(22)
        area = pygame.Rect(margin, hud, w - margin * 2, h - hud - margin)
        self.renderer.layout(area)
        # Centre verticalement le bloc « HUD + plateau » (utile en mode portrait).
        rect = self.renderer.rect
        rect.top = max(hud, (h - rect.h - hud) // 2 + hud)

    # ==== Sauvegarde / restauration ================================================
    def to_state(self):
        body = self.level.spawn_body() if self.state == "dying" else [list(c) for c in self.snake.body]
        direction = self.level.direction if self.state == "dying" else self.snake.direction
        return {
            "mode": self.mode, "level": self.level_num, "score": self.score, "lives": self.lives,
            "apples_total": self.apples_total, "apples_level": self.apples_level,
            "level_score": self.level_score, "lives_lost_level": self.lives_lost_level,
            "max_length": self.max_length, "max_combo": self.max_combo, "elapsed": self.elapsed,
            "body": [list(c) for c in body], "direction": list(direction),
            "items": [{"kind": i.kind, "pos": list(i.pos), "ttl": i.ttl} for i in self.items],
        }

    def _restore(self, s):
        self.level_num = s["level"]
        self.load_level(self.level_num, show_card=True)
        for key in ("score", "lives", "apples_total", "apples_level", "level_score",
                    "lives_lost_level", "max_length", "max_combo", "elapsed"):
            setattr(self, key, s[key])
        self.shown_score = self.score
        body = [tuple(c) for c in s["body"]]
        self.snake = Snake(body, tuple(s["direction"]))
        self.items = [Item(i["kind"], tuple(i["pos"]), 0.0, i["ttl"]) for i in s["items"]]
        if not any(i.kind == "apple" for i in self.items):
            self.spawn_item("apple")

    def autosave(self):
        self.app.db.save_game(self.to_state())

    # ==== Actions du menu pause ==========================================================
    def resume(self):
        self.app.audio.play("pause")
        self.set_state(self.paused_from)

    def restart(self):
        start = self.level_num if self.mode == "aventure" else 1
        self.finished = True
        self.app.change_scene(lambda: GameScene(self.app, mode=self.mode, level=start))

    def save_and_quit(self):
        self.app.db.save_game(self.to_state())
        self.finished = True
        self.go_menu()

    def abandon(self):
        self.finish_game(victory=False)

    def pause(self):
        if self.state in ("intro", "playing"):
            self.paused_from = self.state
            self.set_state("paused")
            self.pause_menu.age = 0.0
            self.app.audio.play("pause")

    # ==== Calculs ========================================================================
    def steps_per_second(self):
        if self.mode == "classique":
            speed = self.level.speed + min(10.0, (self.apples_total // 5) * 0.6)
        else:
            speed = self.level.speed
        speed *= self.difficulty["speed"]
        if "slow" in self.effects:
            speed *= 0.6
        return speed

    def speed_level(self):
        return self.apples_total // 5 + 1

    def point_multiplier(self):
        if self.mode == "aventure":
            base = 1 + 0.25 * (self.level_num - 1)
        else:
            base = 1 + 0.1 * (self.speed_level() - 1)
        mult = base * self.difficulty["score"]
        if "double" in self.effects:
            mult *= 2
        return mult

    def free_cells(self):
        taken = set(self.snake.body) | set(self.level.obstacles) | set(self.portals) | {i.pos for i in self.items}
        hx, hy = self.snake.head
        return [(x, y) for x in range(COLS) for y in range(ROWS)
                if (x, y) not in taken and abs(x - hx) + abs(y - hy) > 2]

    def spawn_item(self, kind):
        cells = self.free_cells()
        if not cells:
            return
        ttl = None
        if kind == "golden":
            ttl = config.GOLDEN_TTL
        elif kind != "apple":
            ttl = config.POWERUP_TTL
        self.items.append(Item(kind, random.choice(cells), self.time, ttl))

    def px(self, cell):
        """Centre d'une case en coordonnées « plateau » (pour particules et textes)."""
        return self.renderer.center(*cell)

    # ==== Événements =======================================================================
    def handle_event(self, event):
        if self.state == "paused":
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_p):
                self.resume()
            else:
                self.pause_menu.handle_event(event)
            return
        if event.type == pygame.WINDOWFOCUSLOST:
            self.pause()
            return
        if event.type != pygame.KEYDOWN:
            return
        if event.key in (pygame.K_ESCAPE, pygame.K_p):
            self.pause()
        elif event.key in KEY_DIRECTIONS and self.state in ("intro", "playing"):
            self.snake.queue_direction(KEY_DIRECTIONS[event.key])
            if self.state == "intro" and self.show_card and self.state_time < CARD_TIME:
                self.state_time = CARD_TIME
        elif event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
            if self.state == "intro" and self.show_card and self.state_time < CARD_TIME:
                self.state_time = CARD_TIME
            elif self.state == "level_complete" and self.state_time > 1.2:
                self.state_time = COMPLETE_TIME

    # ==== Mise à jour ========================================================================
    def update(self, dt):
        if self.state == "paused":
            self.pause_menu.update(dt)
            return
        super().update(dt)
        self.state_time += dt
        self.particles.update(dt)
        self.texts.update(dt)
        self.shake.update(dt)
        self.shown_score += (self.score - self.shown_score) * min(1.0, dt * 10)

        if self.state == "intro":
            intro_len = (CARD_TIME if self.show_card else 0) + COUNT_TIME
            count_t = self.state_time - (CARD_TIME if self.show_card else 0)
            if count_t >= 0:
                tick = int(count_t / (COUNT_TIME / 3))
                if tick != self._last_tick and tick < 3:
                    self._last_tick = tick
                    self.app.audio.play("count")
            if self.state_time >= intro_len:
                self._last_tick = None
                self.app.audio.play("go")
                self.go_timer = 0.6
                self.set_state("playing")
        elif self.state == "playing":
            self._update_playing(dt)
        elif self.state == "dying":
            self._update_dying(dt)
        elif self.state == "level_complete":
            if self.state_time >= COMPLETE_TIME and not self.app.transition:
                self._after_level_complete()
            elif self.state_time < 1.5 and random.random() < dt * 14:
                self._confetti()

    def _update_playing(self, dt):
        self.elapsed += dt
        self.since_eat += dt
        self.go_timer = max(0.0, self.go_timer - dt)
        for name in list(self.effects):
            self.effects[name] -= dt
            if self.effects[name] <= 0:
                del self.effects[name]
        for item in self.items[:]:
            if item.ttl is not None:
                item.ttl -= dt
                if item.ttl <= 0:
                    self.items.remove(item)
        if "ghost" in self.effects and random.random() < dt * 20:
            x, y = self.px(self.snake.head)
            self.particles.burst(x, y, POWERUPS["ghost"]["color"], 1, (10, 40), (1, 3), (0.3, 0.6))

        step = 1.0 / self.steps_per_second()
        self.accumulator += dt
        while self.accumulator >= step and self.state == "playing":
            self.accumulator -= step
            self.step()
        self.move_t = min(1.0, self.accumulator / step) if self.state == "playing" else 1.0

    def step(self):
        snake = self.snake
        dx, dy = snake.next_direction()
        hx, hy = snake.head
        nx, ny = hx + dx, hy + dy
        ghost = "ghost" in self.effects
        if not (0 <= nx < COLS and 0 <= ny < ROWS):
            if self.level.wrap or ghost:
                nx, ny = nx % COLS, ny % ROWS
            else:
                self.die()
                return
        if (nx, ny) in self.portals:
            ex, ey = self.px((nx, ny))
            nx, ny = self.portals[(nx, ny)]
            ox, oy = self.px((nx, ny))
            for x, y in ((ex, ey), (ox, oy)):
                self.particles.burst(x, y, self.theme["accent"], 18, (S(40), S(160)), (S(2), S(4)), glow=True)
            self.app.audio.play("portal")
        if not ghost and ((nx, ny) in self.level.obstacles or (nx, ny) in snake.blocking_cells()):
            self.die()
            return
        snake.move_to((nx, ny))
        self.max_length = max(self.max_length, len(snake.body))
        for item in self.items:
            if item.pos == (nx, ny):
                self.items.remove(item)
                self.collect(item)
                break

    # ==== Ramassage d'objets ==================================================================
    def collect(self, item):
        x, y = self.px(item.pos)
        k = self.renderer.cell / 24
        if item.kind == "apple":
            self.combo = min(config.MAX_COMBO, self.combo + 1) if self.since_eat < config.COMBO_WINDOW else 1
            self.since_eat = 0.0
            self.max_combo = max(self.max_combo, self.combo)
            points = int(round(10 * self.point_multiplier() * self.combo))
            self.snake.grow_pending += 1
            self.apples_total += 1
            self.apples_level += 1
            self.add_points(points, x, y, self.theme["text"])
            if self.combo >= 2:
                self.texts.add(f"COMBO x{self.combo}", x, y - S(30), self.theme["accent2"], 22, 1.1)
            self.particles.burst(x, y, self.theme["food"], 22, (60 * k, 260 * k), (2 * k, 5 * k), glow=True)
            self.app.audio.play(f"eat{self.combo - 1}")
            self.spawn_item("apple")
            self._maybe_spawn_bonus()
            if self.mode == "classique" and self.apples_total % 5 == 0:
                self.texts.add("PLUS VITE !", self.renderer.rect.w / 2, self.renderer.rect.h / 2,
                               self.theme["accent"], 40, 1.4)
            if self.mode == "aventure" and self.apples_level >= self.level.target:
                self.complete_level()
        elif item.kind == "golden":
            points = int(round(50 * self.point_multiplier()))
            self.snake.grow_pending += 2
            self.add_points(points, x, y, GOLD)
            self.particles.burst(x, y, GOLD, 40, (80 * k, 340 * k), (2 * k, 6 * k), glow=True)
            self.shake.add(3)
            self.app.audio.play("golden")
        else:
            info = POWERUPS[item.kind]
            if item.kind == "shrink":
                self.snake.shrink(3)
            else:
                self.effects[item.kind] = info["duration"]
            self.texts.add(info["label"].upper(), x, y, info["color"], 28, 1.2)
            self.particles.burst(x, y, info["color"], 36, (80 * k, 300 * k), (2 * k, 6 * k), glow=True)
            self.app.audio.play("power")

    def add_points(self, points, x, y, color):
        self.score += points
        self.level_score += points
        self.texts.add(f"+{points}", x, y, color, 26)

    def _maybe_spawn_bonus(self):
        kinds = {i.kind for i in self.items}
        if "golden" not in kinds and random.random() < config.GOLDEN_CHANCE:
            self.spawn_item("golden")
        has_power = any(k in POWERUPS for k in kinds)
        if not has_power and (self.level_num >= 2 or self.mode == "classique") \
                and random.random() < config.POWERUP_CHANCE:
            choices = list(POWERUPS)
            if len(self.snake.body) < 7:
                choices.remove("shrink")
            self.spawn_item(random.choice(choices))

    # ==== Mort, niveau terminé, fin de partie ===================================================
    def die(self):
        self.lives -= 1
        self.lives_lost_level += 1
        self.combo = 0
        self.effects.clear()
        self.set_state("dying")
        self.move_t = 1.0
        self.pop_timer = 0.0
        if self.app.settings["screen_shake"]:
            self.shake.add(16)
        x, y = self.px(self.snake.head)
        k = self.renderer.cell / 24
        self.particles.burst(x, y, self.theme["danger"], 50, (100 * k, 420 * k), (2 * k, 7 * k), glow=True)
        self.app.audio.play("die")

    def _update_dying(self, dt):
        self.pop_timer += dt
        interval = min(0.05, 0.9 / max(1, len(self.snake.body)))
        k = self.renderer.cell / 24
        while self.state_time > 0.35 and self.pop_timer >= interval and self.popped < len(self.snake.body):
            self.pop_timer -= interval
            x, y = self.px(self.snake.body[self.popped])
            n = len(self.snake.body)
            col = ui.lerp_color(self.theme["snake_head"], self.theme["snake_tail"], self.popped / max(1, n - 1))
            self.particles.burst(x, y, col, 8, (40 * k, 180 * k), (2 * k, 5 * k), gravity=300 * k)
            self.popped += 1
        if self.state_time >= DEATH_TIME and self.popped >= len(self.snake.body):
            if self.lives > 0:
                self.reset_snake()
                self.effects.clear()
                self.show_card = False
                self.set_state("intro")
            else:
                self.finish_game(victory=False)

    def complete_level(self):
        self.stars = 3 - min(2, self.lives_lost_level)
        self.set_state("level_complete")
        self.app.db.complete_level(self.level_num, self.level_score, self.stars)
        self.app.audio.play("level")
        self._star_sounds = 0
        self.effects.clear()

    def _confetti(self):
        r = self.renderer.rect
        colors = (self.theme["accent"], self.theme["accent2"], self.theme["snake_head"], GOLD)
        k = self.renderer.cell / 24
        self.particles.burst(random.uniform(0, r.w), random.uniform(0, r.h * 0.4), random.choice(colors),
                             10, (60 * k, 260 * k), (2 * k, 5 * k), (0.8, 1.6), gravity=420 * k, drag=1.5)

    def _after_level_complete(self):
        if self.level_num >= MAX_LEVEL:
            self.finish_game(victory=True)
            return

        def next_level():
            self.level_num += 1
            self.particles.clear()
            self.texts.items.clear()
            self.load_level(self.level_num)
            self.autosave()
        self.app.run_transition(next_level)

    def finish_game(self, victory):
        if self.finished:
            return
        self.finished = True
        self.app.db.delete_save()
        result = {
            "mode": self.mode, "score": self.score, "level": self.level_num,
            "apples": self.apples_total, "length": self.max_length, "max_combo": self.max_combo,
            "duration": round(self.elapsed, 1), "difficulty": self.app.settings["difficulty"],
            "victory": victory, "record": self.record,
        }
        from .gameover import GameOverScene
        self.app.change_scene(lambda: GameOverScene(self.app, result))

    def on_quit(self):
        # Fermeture de la fenêtre en pleine partie : on sauvegarde automatiquement.
        if not self.finished and self.lives > 0:
            self.app.db.save_game(self.to_state())

    def on_resize(self):
        self.layout_board()

    # ==== Rendu ===================================================================================
    def draw(self, surf):
        super().draw(surf)
        self.layout_board()
        theme = self.theme
        r = self.renderer
        offset = self.shake.offset()
        ox, oy = r.rect.x + offset[0], r.rect.y + offset[1]

        r.draw_board(surf, self.level, theme, self.app.settings["show_grid"], self.time, offset)
        r.draw_portals(surf, self.level, theme, self.time, offset)
        for item in self.items:
            r.draw_item(surf, item, theme, self.time, offset)
        flash = 0.0
        if self.state == "dying":
            flash = ui.clamp(1 - self.state_time / 0.35) * (0.5 + 0.5 * math.sin(self.state_time * 60))
        t = self.move_t if self.state == "playing" else 1.0
        r.draw_snake(surf, self.snake, t, theme, self.time, offset, ghost="ghost" in self.effects,
                     popped=self.popped, flash=flash, alive=self.state != "dying")
        self.particles.draw(surf, (ox, oy))
        self.texts.draw(surf, (ox, oy))

        if "slow" in self.effects:
            self._draw_tint(surf, POWERUPS["slow"]["color"])
        self._draw_hud(surf)

        if self.state == "intro":
            self._draw_intro(surf)
        elif self.state == "playing" and self.go_timer > 0:
            k = 1 - self.go_timer / 0.6
            ui.draw_text(surf, "GO !", int(S(120) * (1 + 0.4 * k)), theme["accent"], r.rect.center, bold=True,
                         alpha=int(255 * (1 - k)))
        elif self.state == "level_complete":
            self._draw_level_complete(surf)
        elif self.state == "paused":
            self._draw_pause(surf)

    def _draw_tint(self, surf, color):
        r = self.renderer.rect.inflate(S(18), S(18))
        pulse = 0.5 + 0.5 * math.sin(self.time * 4)
        pygame.draw.rect(surf, ui.lerp_color(self.theme["panel"], color, 0.5 + 0.5 * pulse), r, S(4),
                         border_radius=S(16))

    def _draw_hud(self, surf):
        theme = self.theme
        board = self.renderer.rect
        cy = board.top - S(48)
        # Score
        ui.draw_text(surf, "SCORE", S(15), theme["text_dim"], (board.left, cy - S(20)), anchor="midleft", bold=True)
        score_color = POWERUPS["double"]["color"] if "double" in self.effects else theme["text"]
        ui.draw_text(surf, f"{int(round(self.shown_score)):,}".replace(",", " "), S(34), score_color,
                     (board.left, cy + S(8)), anchor="midleft", bold=True)
        best = max(self.record, int(round(self.shown_score)))
        rec_color = GOLD if self.score > self.record else theme["text_dim"]
        ui.draw_text(surf, f"RECORD  {best}", S(15), rec_color, (board.left + S(170), cy - S(20)),
                     anchor="midleft", bold=True)
        if self.combo >= 2 and self.since_eat < config.COMBO_WINDOW:
            k = 1 - self.since_eat / config.COMBO_WINDOW
            ui.draw_text(surf, f"COMBO x{self.combo}", S(22), theme["accent2"], (board.left + S(170), cy + S(8)),
                         anchor="midleft", bold=True)
            bar = pygame.Rect(board.left + S(170), cy + S(24), int(S(110) * k), S(4))
            pygame.draw.rect(surf, theme["accent2"], bar, border_radius=S(2))

        # Niveau et progression
        cx = board.centerx
        if self.mode == "aventure":
            title = f"NIVEAU {self.level_num}  ·  {self.level.name.upper()}"
            progress = self.apples_level / self.level.target
            label = f"{self.apples_level} / {self.level.target}"
        else:
            title = f"CLASSIQUE  ·  VITESSE {self.speed_level()}"
            progress = (self.apples_total % 5) / 5
            label = f"{self.apples_total} pommes"
        ui.draw_text(surf, title, S(19), theme["text"], (cx, cy - S(14)), bold=True)
        bar = pygame.Rect(0, 0, S(260), S(12))
        bar.center = (cx, cy + S(14))
        pygame.draw.rect(surf, ui.darken(theme["panel"], 0.2), bar, border_radius=S(6))
        fill = bar.copy()
        fill.w = max(0, int(bar.w * ui.clamp(progress)))
        if fill.w > 0:
            pygame.draw.rect(surf, theme["accent"], fill, border_radius=S(6))
        pygame.draw.rect(surf, ui.lighten(theme["panel"], 0.15), bar, 1, border_radius=S(6))
        ui.draw_text(surf, label, S(14), theme["text_dim"], (bar.right + S(10), bar.centery), anchor="midleft")

        # Vies et bonus actifs (alignés à droite)
        x = board.right
        for i in range(max(self.lives, 0)):
            pulse = 1 + 0.08 * math.sin(self.time * 5 + i)
            ui.draw_heart(surf, (x - S(14), cy - S(2)), S(24) * pulse, theme["danger"])
            x -= S(32)
        x -= S(12)
        for name, remaining in self.effects.items():
            info = POWERUPS[name]
            center = (x - S(20), cy)
            ui.draw_powerup_icon(surf, name, center, S(34), info["color"], self.time)
            rect = pygame.Rect(0, 0, S(46), S(46))
            rect.center = center
            frac = remaining / info["duration"]
            pygame.draw.arc(surf, info["color"], rect, math.pi / 2, math.pi / 2 + math.tau * frac, S(3))
            x -= S(54)

    def _draw_intro(self, surf):
        theme = self.theme
        board = self.renderer.rect
        if self.show_card and self.state_time < CARD_TIME:
            t = self.state_time
            appear = ui.ease_out_back(t / 0.45)
            alpha = int(255 * ui.clamp((CARD_TIME - t) / 0.3))
            card = pygame.Rect(0, 0, S(560), S(210))
            card.center = (board.centerx, board.centery + int((1 - appear) * S(60)))
            layer = pygame.Surface(card.size, pygame.SRCALPHA)
            ui.draw_panel(layer, layer.get_rect(), theme["panel"], 235, S(22), (*theme["accent"], 255), S(2))
            if self.mode == "aventure":
                head = f"NIVEAU {self.level_num}"
                goal = f"Objectif : {self.level.target} pommes"
            else:
                head = "MODE CLASSIQUE"
                goal = "Survivez le plus longtemps possible"
            w = card.w
            ui.draw_text(layer, head, S(20), theme["accent"], (w // 2, S(40)), bold=True)
            ui.draw_text(layer, self.level.name, S(46), theme["text"], (w // 2, S(88)), bold=True)
            ui.draw_text(layer, self.level.description, S(18), theme["text_dim"], (w // 2, S(136)))
            ui.draw_text(layer, goal, S(18), theme["accent2"], (w // 2, S(172)), bold=True)
            layer.set_alpha(alpha)
            surf.blit(layer, card)
            return
        count_t = self.state_time - (CARD_TIME if self.show_card else 0)
        part = COUNT_TIME / 3
        n = 3 - int(count_t / part)
        if n <= 0:
            return
        p = (count_t % part) / part
        size = int(S(150) * (1.35 - 0.35 * ui.ease_out_cubic(p)))
        ui.blit_glow(surf, board.center, S(150), ui.darken(theme["accent"], 0.6))
        ui.draw_text(surf, str(n), size, theme["text"], board.center, bold=True, alpha=int(255 * (1 - p * 0.7)))

    def _draw_level_complete(self, surf):
        theme = self.theme
        board = self.renderer.rect
        t = self.state_time
        ui.dim_screen(surf, int(110 * ui.clamp(t / 0.4)))
        appear = ui.ease_out_back(t / 0.5)
        card = pygame.Rect(0, 0, S(520), S(260))
        card.center = (board.centerx, board.centery + int((1 - appear) * S(80)))
        ui.draw_panel(surf, card, theme["panel"], 240, S(22), (*GOLD, 255), S(3))
        ui.draw_text(surf, "NIVEAU TERMINÉ !", S(40), GOLD, (card.centerx, card.y + S(50)), bold=True)
        for i in range(3):
            st = (t - 0.5 - i * 0.25) / 0.35
            if st > 0 and i >= self._star_sounds and i < self.stars:
                self._star_sounds += 1
                self.app.audio.play("star")
            scale = ui.ease_out_back(st) if i < self.stars else 1.0
            center = (card.centerx + (i - 1) * S(76), card.y + S(124))
            ui.draw_star(surf, center, S(30), ui.darken(theme["panel"], 0.4))
            if i < self.stars and scale > 0:
                ui.blit_glow(surf, center, S(60) * scale, ui.darken(GOLD, 0.6))
                ui.draw_star(surf, center, S(30) * scale, GOLD, ui.lighten(GOLD, 0.5))
        ui.draw_text(surf, f"Points du niveau : {self.level_score}", S(20), theme["text"],
                     (card.centerx, card.y + S(188)))
        if t > 1.2:
            msg = "Victoire finale !" if self.level_num >= MAX_LEVEL else "Entrée pour continuer"
            ui.draw_text(surf, msg, S(16), theme["text_dim"], (card.centerx, card.y + S(226)),
                         alpha=int(160 + 90 * math.sin(self.time * 4)))

    def _draw_pause(self, surf):
        theme = self.theme
        w, h = surf.get_size()
        ui.dim_screen(surf, 170)
        panel = pygame.Rect(0, 0, S(480), S(130) + self.pause_menu.total_height())
        panel.center = (w // 2, h // 2)
        ui.draw_panel(surf, panel, theme["panel"], 235, S(24), (*theme["accent"], 255), S(2))
        ui.draw_text(surf, "PAUSE", S(48), theme["text"], (w // 2, panel.y + S(56)), bold=True)
        self.pause_menu.layout(w // 2, panel.y + S(105))
        self.pause_menu.draw(surf, theme)
