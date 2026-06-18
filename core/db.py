import sqlite3
from datetime import datetime
from flask import current_app, g


def now_iso():
    return datetime.utcnow().isoformat()


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(
            current_app.config["DATABASE"],
            isolation_level=None,
        )
        g.db.row_factory = sqlite3.Row

    return g.db


def close_db(error=None):
    db = g.pop("db", None)

    if db is not None:
        db.close()


def init_db(app):
    from core.jackpots import JACKPOT_SEEDS

    db = sqlite3.connect(app.config["DATABASE"])
    db.row_factory = sqlite3.Row

    db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            balance REAL NOT NULL DEFAULT 1000,
            free_spins INTEGER NOT NULL DEFAULT 0,
            free_spin_bet INTEGER NOT NULL DEFAULT 10,
            created_at TEXT NOT NULL
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS jackpots (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            mini REAL NOT NULL,
            minor REAL NOT NULL,
            major REAL NOT NULL,
            grand REAL NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS game_rounds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            game TEXT NOT NULL,
            bet REAL NOT NULL,
            mode TEXT NOT NULL,
            win REAL NOT NULL,
            jackpot_award TEXT,
            jackpot_win REAL NOT NULL DEFAULT 0,
            data_json TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    row = db.execute("SELECT id FROM jackpots WHERE id = 1").fetchone()

    if not row:
        db.execute(
            """
            INSERT INTO jackpots (id, mini, minor, major, grand, updated_at)
            VALUES (1, ?, ?, ?, ?, ?)
            """,
            (
                JACKPOT_SEEDS["MINI"],
                JACKPOT_SEEDS["MINOR"],
                JACKPOT_SEEDS["MAJOR"],
                JACKPOT_SEEDS["GRAND"],
                now_iso(),
            ),
        )

    db.commit()
    db.close()