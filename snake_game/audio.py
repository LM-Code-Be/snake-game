"""Sons et musique générés par synthèse : aucun fichier audio externe n'est nécessaire."""
import io
import math
import random
import threading
import wave
from array import array

import pygame

from .config import DATA_DIR

RATE = 22050
MUSIC_FILE = DATA_DIR / "music_v1.wav"


def midi(note):
    return 440.0 * 2 ** ((note - 69) / 12)


def tone(freq, dur, wave_type="square", vol=0.4, freq_end=None, attack=0.004, release=0.05, duty=0.5):
    """Génère une note (liste de flottants entre -1 et 1)."""
    n = max(1, int(RATE * dur))
    out = [0.0] * n
    phase = 0.0
    df = (freq_end - freq) if freq_end else 0.0
    att = max(1, int(attack * RATE))
    rel = max(1, int(release * RATE))
    sin, tau, rnd = math.sin, math.tau, random.random
    for i in range(n):
        phase = (phase + (freq + df * i / n) / RATE) % 1.0
        if wave_type == "sine":
            v = sin(tau * phase)
        elif wave_type == "square":
            v = 1.0 if phase < duty else -1.0
        elif wave_type == "tri":
            v = 4.0 * abs(phase - 0.5) - 1.0
        elif wave_type == "saw":
            v = 2.0 * phase - 1.0
        else:
            v = rnd() * 2.0 - 1.0
        env = i / att if i < att else 1.0
        if n - i < rel:
            env *= (n - i) / rel
        out[i] = v * vol * env
    return out


def mix_into(base, part, start=0.0):
    """Ajoute `part` dans `base` à partir de `start` secondes."""
    offset = int(start * RATE)
    end = offset + len(part)
    if end > len(base):
        base.extend([0.0] * (end - len(base)))
    for i, v in enumerate(part):
        base[offset + i] += v
    return base


def sequence(*parts):
    out = []
    for p in parts:
        out.extend(p)
    return out


def to_wav_bytes(samples, normalize=False):
    peak = max(1e-6, max(abs(v) for v in samples)) if normalize else 1.0
    gain = 0.9 / peak if normalize else 1.0
    data = array("h", (int(max(-1.0, min(1.0, v * gain)) * 32767) for v in samples))
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(data.tobytes())
    return buf.getvalue()


def build_sound_bank():
    s = {}
    for i, k in enumerate((1.0, 1.12, 1.26, 1.34, 1.5)):
        s[f"eat{i}"] = mix_into(tone(520 * k, 0.09, "square", 0.22, 900 * k, duty=0.25),
                                tone(1040 * k, 0.07, "sine", 0.18))
    s["golden"] = sequence(*(tone(midi(n), 0.07, "square", 0.2, duty=0.25, release=0.03)
                             for n in (72, 76, 79, 84, 88)))
    s["power"] = mix_into(tone(300, 0.3, "tri", 0.4, 1300), tone(1800, 0.25, "sine", 0.1, 2600), 0.05)
    s["die"] = mix_into(tone(420, 0.55, "saw", 0.3, 50, release=0.2), tone(0, 0.45, "noise", 0.25, release=0.3))
    s["level"] = sequence(tone(midi(67), 0.11, "square", 0.22, duty=0.3), tone(midi(72), 0.11, "square", 0.22, duty=0.3),
                          tone(midi(76), 0.11, "square", 0.22, duty=0.3),
                          mix_into(tone(midi(79), 0.45, "square", 0.2, duty=0.3, release=0.25),
                                   tone(midi(84), 0.45, "sine", 0.2, release=0.25)))
    s["gameover"] = sequence(*(tone(midi(n), d, "tri", 0.45, release=0.08)
                               for n, d in ((64, 0.22), (62, 0.22), (60, 0.22), (55, 0.6))))
    s["click"] = tone(880, 0.05, "tri", 0.45, 660)
    s["hover"] = tone(1300, 0.025, "sine", 0.2)
    s["count"] = tone(520, 0.14, "square", 0.18, duty=0.3)
    s["go"] = mix_into(tone(1040, 0.35, "square", 0.18, duty=0.3, release=0.2), tone(780, 0.35, "sine", 0.2))
    s["portal"] = sequence(tone(900, 0.1, "sine", 0.35, 300), tone(300, 0.12, "sine", 0.35, 1100))
    s["pause"] = sequence(tone(660, 0.07, "tri", 0.4), tone(440, 0.1, "tri", 0.4))
    s["star"] = tone(1568, 0.18, "sine", 0.3, 2093, release=0.12)
    return s


def build_music():
    """Petite boucle chiptune (La m - Fa - Do - Sol) d'environ 17 secondes."""
    beat = 60 / 110
    chords = [(57, 60, 64), (53, 57, 60), (48, 52, 55), (55, 59, 62)]
    pattern = (0, 1, 2, 1, 0, 2, 1, 2)
    out = []
    for rep in range(2):
        for bar, chord in enumerate(chords):
            t0 = (rep * 4 + bar) * 4 * beat
            root = chord[0] - 24 if chord[0] >= 55 else chord[0] - 12
            for b in range(4):
                note = root + (12 if b == 2 else 0)
                mix_into(out, tone(midi(note), beat * 0.85, "tri", 0.32, release=0.12), t0 + b * beat)
                if b in (0, 2):
                    mix_into(out, tone(130, 0.12, "sine", 0.45, 40, release=0.06), t0 + b * beat)
            for e in range(8):
                note = chord[pattern[e]] + 12 + (12 if rep == 1 and e % 4 == 3 else 0)
                start = t0 + e * beat / 2
                mix_into(out, tone(midi(note), beat * 0.45, "square", 0.07, duty=0.25, release=0.1), start)
                mix_into(out, tone(midi(note), beat * 0.45, "sine", 0.09, release=0.1), start)
                if e % 2 == 1:
                    mix_into(out, tone(0, 0.03, "noise", 0.06, release=0.02), start)
    total = int(8 * 4 * beat * RATE)
    return out[:total]


class Audio:
    def __init__(self, settings):
        self.enabled = pygame.mixer.get_init() is not None
        self.sounds = {}
        self.music = None
        self._music_ready = None
        self._music_started = False
        self.settings = settings
        if not self.enabled:
            return
        pygame.mixer.set_num_channels(24)
        pygame.mixer.set_reserved(1)
        self.music_channel = pygame.mixer.Channel(0)
        for name, samples in build_sound_bank().items():
            self.sounds[name] = pygame.mixer.Sound(io.BytesIO(to_wav_bytes(samples)))
        self.apply_volumes()

    def play(self, name):
        sound = self.sounds.get(name)
        if sound is not None:
            sound.play()

    def apply_volumes(self):
        if not self.enabled:
            return
        sfx = self.settings["sfx_volume"] / 10
        for sound in self.sounds.values():
            sound.set_volume(sfx)
        if self.music is not None:
            self.music.set_volume(self.settings["music_volume"] / 10 * 0.55)

    # La musique est générée (ou relue depuis le cache) dans un thread pour ne pas
    # bloquer le démarrage ; `update` la lance dès qu'elle est prête.
    def start_music(self):
        if not self.enabled or self._music_started:
            return
        self._music_started = True
        threading.Thread(target=self._load_music, daemon=True).start()

    def _load_music(self):
        try:
            if not MUSIC_FILE.exists():
                MUSIC_FILE.parent.mkdir(parents=True, exist_ok=True)
                MUSIC_FILE.write_bytes(to_wav_bytes(build_music(), normalize=True))
            self._music_ready = pygame.mixer.Sound(str(MUSIC_FILE))
        except (OSError, pygame.error):
            self._music_ready = None

    def update(self):
        if self._music_ready is not None and self.music is None:
            self.music = self._music_ready
            self.apply_volumes()
            self.music_channel.play(self.music, loops=-1, fade_ms=2000)
