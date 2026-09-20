from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT,
    created_at TEXT NOT NULL,
    stripe_customer_id TEXT,
    plan TEXT,
    entitlement_active INTEGER NOT NULL DEFAULT 0,
    entitlement_checked_at TEXT
);

CREATE TABLE IF NOT EXISTS auth_tokens (
    token_hash TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    name TEXT,
    created_at TEXT NOT NULL,
    expires_at TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS training_sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    client_session_id TEXT,
    track TEXT NOT NULL,
    car TEXT NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    best_lap_s REAL,
    reference_source TEXT,
    bind_ok INTEGER NOT NULL DEFAULT 0,
    summary_json TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS device_codes (
    code TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    consumed INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS best_laps (
    user_id TEXT NOT NULL,
    track TEXT NOT NULL,
    car TEXT NOT NULL,
    lap_time_s REAL NOT NULL,
    session_id TEXT,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (user_id, track, car)
);

CREATE TABLE IF NOT EXISTS point_events (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    session_id TEXT,
    kind TEXT NOT NULL,
    points INTEGER NOT NULL,
    detail TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS coaching_cards (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    session_id TEXT,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    tone TEXT,
    created_at TEXT NOT NULL
);
"""


def _migrate(conn: sqlite3.Connection) -> None:
    cols = {row[1] for row in conn.execute("PRAGMA table_info(training_sessions)").fetchall()}
    if cols and "client_session_id" not in cols:
        conn.execute("ALTER TABLE training_sessions ADD COLUMN client_session_id TEXT")
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_training_client
        ON training_sessions(user_id, client_session_id)
        WHERE client_session_id IS NOT NULL
        """
    )


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    _migrate(conn)
    return conn


@contextmanager
def session(path: Path):
    conn = connect(path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
