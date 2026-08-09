"""
SQLite-backed storage for SiraTech gamification (XP, discoveries, badges).

This is a deliberately swappable prototype: it exposes a small,
data-access-only interface (record a discovery, list discoveries, unlock a
badge, list badges) so that `gamification_service.py` — where all the XP
and badge *rules* live — never touches SQL directly. Swapping this out for
a production database later (Postgres, etc.) means rewriting this one
module; nothing else needs to change. This mirrors the isolation pattern
`data_loader.py` uses for the read-only seed JSON files, except this store
is written to at request time instead of just read.

Idempotency ("never reward the same discovery repeatedly") is enforced at
the storage layer via a composite primary key on
(user_id, discovery_type, item_id) — a duplicate INSERT simply fails and
`record_discovery()` reports that cleanly instead of raising.
"""

import os
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


class GamificationRepository:
    """Thin data-access layer over a single SQLite file."""

    def __init__(self, db_path):
        self.db_path = db_path
        self._lock = threading.Lock()
        if db_path != ":memory:":
            dir_name = os.path.dirname(db_path)
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)
        self._init_schema()

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_schema(self):
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS discoveries (
                    user_id TEXT NOT NULL,
                    discovery_type TEXT NOT NULL,
                    item_id TEXT NOT NULL,
                    location_id TEXT,
                    xp_awarded INTEGER NOT NULL DEFAULT 0,
                    discovered_at TEXT NOT NULL,
                    PRIMARY KEY (user_id, discovery_type, item_id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS badges (
                    user_id TEXT NOT NULL,
                    badge_code TEXT NOT NULL,
                    unlocked_at TEXT NOT NULL,
                    PRIMARY KEY (user_id, badge_code)
                )
                """
            )

    # -- discoveries ---------------------------------------------------

    def discovery_exists(self, user_id, discovery_type, item_id):
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM discoveries WHERE user_id = ? AND discovery_type = ? AND item_id = ?",
                (user_id, discovery_type, item_id),
            ).fetchone()
            return row is not None

    def record_discovery(self, user_id, discovery_type, item_id, location_id, xp_awarded):
        """
        Insert a new discovery row. Returns True if this was a genuinely
        new (user, type, item) discovery, False if it was already
        recorded (in which case nothing changes — no double XP).
        """
        with self._lock, self._connect() as conn:
            try:
                conn.execute(
                    """
                    INSERT INTO discoveries
                        (user_id, discovery_type, item_id, location_id, xp_awarded, discovered_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (user_id, discovery_type, item_id, location_id, xp_awarded, _now_iso()),
                )
                return True
            except sqlite3.IntegrityError:
                return False

    def list_discoveries(self, user_id, discovery_type=None):
        with self._connect() as conn:
            if discovery_type:
                rows = conn.execute(
                    "SELECT * FROM discoveries WHERE user_id = ? AND discovery_type = ? "
                    "ORDER BY discovered_at",
                    (user_id, discovery_type),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM discoveries WHERE user_id = ? ORDER BY discovered_at",
                    (user_id,),
                ).fetchall()
            return [dict(row) for row in rows]

    def total_xp(self, user_id):
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COALESCE(SUM(xp_awarded), 0) AS total FROM discoveries WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            return row["total"]

    def count_by_type(self, user_id, discovery_type):
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS n FROM discoveries WHERE user_id = ? AND discovery_type = ?",
                (user_id, discovery_type),
            ).fetchone()
            return row["n"]

    def distinct_locations(self, user_id, discovery_type=None):
        with self._connect() as conn:
            if discovery_type:
                rows = conn.execute(
                    """
                    SELECT DISTINCT location_id FROM discoveries
                    WHERE user_id = ? AND discovery_type = ? AND location_id IS NOT NULL
                    """,
                    (user_id, discovery_type),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT DISTINCT location_id FROM discoveries "
                    "WHERE user_id = ? AND location_id IS NOT NULL",
                    (user_id,),
                ).fetchall()
            return {row["location_id"] for row in rows}

    # -- badges ----------------------------------------------------------

    def unlocked_badge_codes(self, user_id):
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT badge_code FROM badges WHERE user_id = ?", (user_id,)
            ).fetchall()
            return {row["badge_code"] for row in rows}

    def unlock_badge(self, user_id, badge_code):
        """Idempotent: returns True if newly unlocked, False if the user already had it."""
        with self._lock, self._connect() as conn:
            try:
                conn.execute(
                    "INSERT INTO badges (user_id, badge_code, unlocked_at) VALUES (?, ?, ?)",
                    (user_id, badge_code, _now_iso()),
                )
                return True
            except sqlite3.IntegrityError:
                return False

    def list_badges(self, user_id):
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT badge_code, unlocked_at FROM badges WHERE user_id = ? ORDER BY unlocked_at",
                (user_id,),
            ).fetchall()
            return [dict(row) for row in rows]


_repositories = {}
_repositories_lock = threading.Lock()


def get_repository(db_path):
    """
    Return a process-wide GamificationRepository for the given db_path,
    creating it on first use. Keyed by path so tests pointed at an
    isolated `GAMIFICATION_DB_PATH` (e.g. a tmp file) never share state
    with the dev database or with each other.
    """
    with _repositories_lock:
        if db_path not in _repositories:
            _repositories[db_path] = GamificationRepository(db_path)
        return _repositories[db_path]
