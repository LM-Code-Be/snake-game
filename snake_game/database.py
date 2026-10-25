"""Persistance locale SQLite : paramètres, scores, historique, progression et sauvegarde."""
import json
import sqlite3
from datetime import datetime

SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS scores (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    player      TEXT    NOT NULL,
    mode        TEXT    NOT NULL,
    score       INTEGER NOT NULL,
    level       INTEGER NOT NULL,
    apples      INTEGER NOT NULL,
    length      INTEGER NOT NULL,
    max_combo   INTEGER NOT NULL,
    duration    REAL    NOT NULL,
    difficulty  TEXT    NOT NULL,
    victory     INTEGER NOT NULL DEFAULT 0,
    played_at   TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_scores_mode_score ON scores (mode, score DESC);

CREATE TABLE IF NOT EXISTS level_progress (
    level        INTEGER PRIMARY KEY,
    best_score   INTEGER NOT NULL DEFAULT 0,
    stars        INTEGER NOT NULL DEFAULT 0,
    completed_at TEXT
);

CREATE TABLE IF NOT EXISTS saved_game (
    slot     INTEGER PRIMARY KEY CHECK (slot = 1),
    data     TEXT NOT NULL,
    saved_at TEXT NOT NULL
);
"""


def _now():
    return datetime.now().isoformat(timespec="seconds")


class Database:
    def __init__(self, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def close(self):
        self.conn.close()

    # --- Paramètres --------------------------------------------------------
    def load_settings(self, defaults):
        settings = dict(defaults)
        for row in self.conn.execute("SELECT key, value FROM settings"):
            if row["key"] in defaults:
                try:
                    settings[row["key"]] = json.loads(row["value"])
                except json.JSONDecodeError:
                    pass
        return settings

    def save_setting(self, key, value):
        self.conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, json.dumps(value)))
        self.conn.commit()

    # --- Scores & historique ------------------------------------------------------
    def add_score(self, player, result):
        cur = self.conn.execute(
            "INSERT INTO scores (player, mode, score, level, apples, length, max_combo, duration,"
            " difficulty, victory, played_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (player, result["mode"], result["score"], result["level"], result["apples"],
             result["length"], result["max_combo"], result["duration"], result["difficulty"],
             int(result["victory"]), _now()))
        self.conn.commit()
        return cur.lastrowid

    def top_scores(self, mode, limit=10):
        return self.conn.execute(
            "SELECT * FROM scores WHERE mode = ? ORDER BY score DESC, played_at ASC LIMIT ?",
            (mode, limit)).fetchall()

    def recent_games(self, limit=10):
        return self.conn.execute(
            "SELECT * FROM scores ORDER BY played_at DESC, id DESC LIMIT ?", (limit,)).fetchall()

    def best_score(self, mode):
        row = self.conn.execute("SELECT MAX(score) AS best FROM scores WHERE mode = ?", (mode,)).fetchone()
        return row["best"] or 0

    def rank_of(self, mode, score):
        """Rang qu'obtiendrait ce score dans le classement du mode (1 = meilleur)."""
        row = self.conn.execute("SELECT COUNT(*) AS n FROM scores WHERE mode = ? AND score > ?",
                                (mode, score)).fetchone()
        return row["n"] + 1

    def stats(self):
        row = self.conn.execute(
            "SELECT COUNT(*) AS games, COALESCE(SUM(apples), 0) AS apples,"
            " COALESCE(SUM(duration), 0) AS duration, COALESCE(MAX(score), 0) AS best,"
            " COALESCE(MAX(length), 0) AS longest, COALESCE(MAX(max_combo), 0) AS combo,"
            " COALESCE(AVG(score), 0) AS average, COALESCE(SUM(victory), 0) AS victories"
            " FROM scores").fetchone()
        levels = self.conn.execute(
            "SELECT COUNT(*) AS done, COALESCE(SUM(stars), 0) AS stars FROM level_progress").fetchone()
        stats = dict(row)
        stats["levels_done"] = levels["done"]
        stats["stars"] = levels["stars"]
        return stats

    # --- Progression du mode Aventure -------------------------------------------------
    def level_progress(self):
        return {row["level"]: {"best": row["best_score"], "stars": row["stars"]}
                for row in self.conn.execute("SELECT * FROM level_progress")}

    def unlocked_level(self, max_level):
        row = self.conn.execute("SELECT MAX(level) AS last FROM level_progress").fetchone()
        return min(max_level, (row["last"] or 0) + 1)

    def complete_level(self, level, score, stars):
        self.conn.execute(
            "INSERT INTO level_progress (level, best_score, stars, completed_at) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(level) DO UPDATE SET best_score = MAX(best_score, excluded.best_score),"
            " stars = MAX(stars, excluded.stars), completed_at = excluded.completed_at",
            (level, score, stars, _now()))
        self.conn.commit()

    # --- Sauvegarde « Continuer » ---------------------------------------------------------
    def save_game(self, state):
        self.conn.execute(
            "INSERT INTO saved_game (slot, data, saved_at) VALUES (1, ?, ?) "
            "ON CONFLICT(slot) DO UPDATE SET data = excluded.data, saved_at = excluded.saved_at",
            (json.dumps(state), _now()))
        self.conn.commit()

    def load_game(self):
        row = self.conn.execute("SELECT data FROM saved_game WHERE slot = 1").fetchone()
        if row is None:
            return None
        try:
            return json.loads(row["data"])
        except json.JSONDecodeError:
            return None

    def delete_save(self):
        self.conn.execute("DELETE FROM saved_game")
        self.conn.commit()

    def reset_all(self):
        self.conn.executescript("DELETE FROM scores; DELETE FROM level_progress; DELETE FROM saved_game;")
        self.conn.commit()
