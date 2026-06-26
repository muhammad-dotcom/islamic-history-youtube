"""SQLite upload log.

Tracks every video produced: topic, YouTube video ID, timestamp.
Prevents re-uploading the same topic.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .config import DB_PATH


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS uploads (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            topic       TEXT NOT NULL,
            video_id    TEXT,
            uploaded_at TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn


def mark_uploaded(topic: str, video_id: str | None) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO uploads (topic, video_id, uploaded_at) VALUES (?, ?, ?)",
            (topic, video_id, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()


def already_uploaded(topic: str) -> bool:
    with _connect() as conn:
        row = conn.execute(
            "SELECT 1 FROM uploads WHERE topic = ? LIMIT 1", (topic,)
        ).fetchone()
    return row is not None


def list_uploads() -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT topic, video_id, uploaded_at FROM uploads ORDER BY uploaded_at DESC"
        ).fetchall()
    return [{"topic": r[0], "video_id": r[1], "uploaded_at": r[2]} for r in rows]
