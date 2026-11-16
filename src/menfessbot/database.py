"""SQLite persistence for submissions, limits, and retention."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sqlite3


def _utc(value: datetime | None = None) -> datetime:
    value = value or datetime.now(timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class SubmissionStore:
    def __init__(self, database_path: str):
        self.database_path = database_path
        if database_path != ":memory:":
            Path(database_path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS submissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_chat_id INTEGER NOT NULL,
                    source_message_id INTEGER NOT NULL,
                    sender_user_id INTEGER,
                    status TEXT NOT NULL DEFAULT 'pending'
                        CHECK(status IN ('pending', 'approved', 'rejected')),
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    reviewed_at TEXT,
                    UNIQUE(source_chat_id, source_message_id)
                )
            """)
            db.execute("""
                CREATE TABLE IF NOT EXISTS moderation_claims (
                    submission_id INTEGER PRIMARY KEY
                        REFERENCES submissions(id) ON DELETE CASCADE,
                    claimed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            db.execute("CREATE INDEX IF NOT EXISTS idx_submissions_user_created ON submissions(sender_user_id, created_at)")
            db.execute("CREATE INDEX IF NOT EXISTS idx_submissions_status_created ON submissions(status, created_at)")

    def _connect(self):
        db = sqlite3.connect(self.database_path, timeout=10)
        db.row_factory = sqlite3.Row
        return db

    def add(self, chat_id: int, message_id: int, sender_user_id: int | None) -> int:
        with self._connect() as db:
            cursor = db.execute(
                "INSERT INTO submissions (source_chat_id, source_message_id, sender_user_id) VALUES (?, ?, ?)",
                (chat_id, message_id, sender_user_id))
            return int(cursor.lastrowid)

    def add_with_limits(
        self, chat_id: int, message_id: int, sender_user_id: int | None,
        *, cooldown_seconds: int, hourly_limit: int, now: datetime | None = None,
    ) -> int | None:
        """Insert atomically, returning None when the user's limit is reached."""
        if sender_user_id is None:
            raise ValueError("sender_user_id is required for rate limiting")
        if cooldown_seconds < 0 or hourly_limit < 1:
            raise ValueError("Invalid rate-limit configuration")
        current = _utc(now)
        current_text = current.strftime("%Y-%m-%d %H:%M:%S")
        window_start = (current - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
        cooldown_start = (current - timedelta(seconds=cooldown_seconds)).strftime("%Y-%m-%d %H:%M:%S")
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            recent = db.execute(
                """SELECT COUNT(*) AS amount
                   FROM submissions
                   WHERE sender_user_id = ? AND created_at >= ?""",
                (sender_user_id, window_start)).fetchone()
            if recent["amount"] >= hourly_limit:
                return None
            if cooldown_seconds:
                latest = db.execute(
                    """SELECT MAX(created_at) AS latest
                       FROM submissions
                       WHERE sender_user_id = ? AND created_at >= ?""",
                    (sender_user_id, cooldown_start)).fetchone()["latest"]
                if latest is not None:
                    return None
            cursor = db.execute(
                """INSERT INTO submissions
                   (source_chat_id, source_message_id, sender_user_id, created_at)
                   VALUES (?, ?, ?, ?)""",
                (chat_id, message_id, sender_user_id, current_text))
            return int(cursor.lastrowid)

    def get(self, submission_id: int):
        with self._connect() as db:
            row = db.execute("SELECT * FROM submissions WHERE id = ?", (submission_id,)).fetchone()
            return dict(row) if row else None

    def claim(self, submission_id: int) -> bool:
        """Atomically claim a pending review; reclaim abandoned claims after 10 minutes."""
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("DELETE FROM moderation_claims WHERE claimed_at < datetime('now', '-10 minutes')")
            pending = db.execute(
                "SELECT 1 FROM submissions WHERE id = ? AND status = 'pending'",
                (submission_id,)).fetchone()
            if not pending:
                return False
            try:
                db.execute("INSERT INTO moderation_claims (submission_id) VALUES (?)", (submission_id,))
                return True
            except sqlite3.IntegrityError:
                return False

    def release_claim(self, submission_id: int) -> None:
        with self._connect() as db:
            db.execute("DELETE FROM moderation_claims WHERE submission_id = ?", (submission_id,))

    def set_status(self, submission_id: int, status: str) -> bool:
        if status not in {"approved", "rejected"}:
            raise ValueError("status must be approved or rejected")
        with self._connect() as db:
            result = db.execute(
                "UPDATE submissions SET status = ?, reviewed_at = CURRENT_TIMESTAMP WHERE id = ? AND status = 'pending'",
                (status, submission_id))
            if result.rowcount == 1:
                db.execute("DELETE FROM moderation_claims WHERE submission_id = ?", (submission_id,))
                return True
            return False

    def prune_reviewed(self, retention_days: int, *, now: datetime | None = None) -> int:
        """Delete only reviewed rows older than retention; pending items are never deleted."""
        if retention_days < 1:
            raise ValueError("retention_days must be at least 1")
        cutoff = (_utc(now) - timedelta(days=retention_days)).strftime("%Y-%m-%d %H:%M:%S")
        with self._connect() as db:
            result = db.execute(
                """DELETE FROM submissions
                   WHERE status IN ('approved', 'rejected') AND COALESCE(reviewed_at, created_at) < ?""",
                (cutoff,))
            return result.rowcount
