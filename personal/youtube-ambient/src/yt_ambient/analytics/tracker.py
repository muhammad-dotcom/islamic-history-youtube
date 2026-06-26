"""Analytics tracker — Phase 2 stub.

Logs uploaded videos to SQLite and (in Phase 2) fetches view counts from the
YouTube Analytics API to inform the weighted scheduler.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path


class AnalyticsTracker:
    def __init__(self, db_path: Path | str = "data/analytics.db") -> None:
        self.db_path = Path(db_path)
        self._init_db()

    def log_upload(
        self,
        video_id: str,
        sound_type: str,
        duration_hours: float,
        title: str,
    ) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO videos
                    (video_id, sound_type, duration_hours, title, uploaded_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (video_id, sound_type, duration_hours, title, datetime.utcnow().isoformat()),
            )

    def get_view_weights(self) -> dict[str, float]:
        """Return normalized view-count weights per sound type (Phase 2)."""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT sound_type, SUM(view_count) FROM videos GROUP BY sound_type"
            ).fetchall()

        if not rows:
            return {}

        total = sum(r[1] or 0 for r in rows) or 1
        return {r[0]: (r[1] or 0) / total for r in rows}

    def _init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS videos (
                    video_id      TEXT PRIMARY KEY,
                    sound_type    TEXT NOT NULL,
                    duration_hours REAL NOT NULL,
                    title         TEXT,
                    uploaded_at   TEXT,
                    view_count    INTEGER DEFAULT 0
                )
                """
            )

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)
