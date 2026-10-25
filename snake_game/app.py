"""Application : fenêtre responsive, boucle principale, scènes et transitions."""
import sys

import pygame

from . import config, ui
from .audio import Audio
from .database import Database
from .effects import Background, Transition


def _enable_dpi_awareness():
    """Évite le flou de Windows sur les écrans à mise à l'échelle (125 %, 150 %...)."""
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except (AttributeError, OSError):
            pass


class App:
    def __init__(self):
        _enable_dpi_awareness()
        pygame.mixer.pre_init(44100, -16, 2, 512)
        pygame.init()
        pygame.display.set_caption(config.TITLE)
        pygame.display.set_icon(ui.make_icon())

        self.db = Database(config.DB_PATH)
        self.settings = self.db.load_settings(config.DEFAULT_SETTINGS)
        self.windowed_size = config.DEFAULT_WINDOW
        self.screen = self._create_window(self.settings["fullscreen"])
        ui.set_scale(*self.screen.get_size())

        self.clock = pygame.time.Clock()
        self.audio = Audio(self.settings)
        self.background = Background()
        self.transition = None
        self.running = True

        from .scenes.menu import MenuScene
        self.scene = MenuScene(self)
        self.audio.start_music()

    # --- Fenêtre ------------------------------------------------------------------
    def _create_window(self, fullscreen):
        if fullscreen:
            return pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        return pygame.display.set_mode(self.windowed_size, pygame.RESIZABLE)

    def set_fullscreen(self, enabled):
        if not enabled and self.screen.get_flags() & pygame.FULLSCREEN == 0:
            return
        if enabled:
            self.windowed_size = self.screen.get_size()
        self.screen = self._create_window(enabled)
        self.on_resize()

    def on_resize(self):
        self.screen = pygame.display.get_surface()
        ui.set_scale(*self.screen.get_size())
        if hasattr(self.scene, "on_resize"):
            self.scene.on_resize()

    @property
    def theme(self):
        return config.THEMES[self.settings["theme"]]

    def set_setting(self, key, value):
        self.settings[key] = value
        self.db.save_setting(key, value)
        if key in ("music_volume", "sfx_volume"):
            self.audio.apply_volumes()
        elif key == "fullscreen":
            self.set_fullscreen(value)

    # --- Scènes & transitions ------------------------------------------------------------
    def run_transition(self, callback):
        if self.transition is None:
            self.transition = Transition(callback)

    def change_scene(self, make_scene):
        """`make_scene` est appelé quand l'écran est couvert (construction invisible)."""
        def swap():
            self.scene.on_exit()
            self.scene = make_scene()
        self.run_transition(swap)

    def quit(self):
        self.running = False

    # --- Boucle principale ------------------------------------------------------------------
    def handle_global_event(self, event):
        if event.type == pygame.QUIT:
            self.quit()
            return True
        if event.type in (pygame.VIDEORESIZE, pygame.WINDOWSIZECHANGED):
            self.on_resize()
            return True
        if event.type == pygame.KEYDOWN and (event.key == pygame.K_F11 or
                                             (event.key == pygame.K_RETURN and event.mod & pygame.KMOD_ALT)):
            self.set_setting("fullscreen", not self.settings["fullscreen"])
            return True
        return False

    def run(self):
        while self.running:
            dt = min(self.clock.tick(config.FPS) / 1000.0, 0.05)
            for event in pygame.event.get():
                if self.handle_global_event(event):
                    continue
                if self.transition is None:
                    self.scene.handle_event(event)
            self.audio.update()
            self.background.update(dt)
            self.scene.update(dt)
            if self.transition:
                self.transition.update(dt)
                if self.transition.done:
                    self.transition = None
            self.draw()
        self.scene.on_quit()
        self.db.close()
        pygame.quit()

    def draw(self):
        surf = self.screen
        self.scene.draw(surf)
        if self.transition:
            self.transition.draw(surf, self.theme)
        if self.settings["show_fps"]:
            ui.draw_text(surf, f"{self.clock.get_fps():.0f} FPS", ui.S(16), (200, 255, 200),
                         (surf.get_width() - ui.S(12), ui.S(12)), anchor="topright")
        pygame.display.flip()
