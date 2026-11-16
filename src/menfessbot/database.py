"""SQLite persistence for submissions."""
from pathlib import Path
import sqlite3

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

    def _connect(self):
        db = sqlite3.connect(self.database_path)
        db.row_factory = sqlite3.Row
        return db

    def add(self, chat_id: int, message_id: int, sender_user_id: int | None) -> int:
        with self._connect() as db:
            cursor = db.execute(
                "INSERT INTO submissions (source_chat_id, source_message_id, sender_user_id) VALUES (?, ?, ?)",
                (chat_id, message_id, sender_user_id))
            return int(cursor.lastrowid)

    def get(self, submission_id: int):
        with self._connect() as db:
            row = db.execute("SELECT * FROM submissions WHERE id = ?", (submission_id,)).fetchone()
            return dict(row) if row else None

    def set_status(self, submission_id: int, status: str) -> bool:
        if status not in {"approved", "rejected"}:
            raise ValueError("status must be approved or rejected")
        with self._connect() as db:
            result = db.execute(
                "UPDATE submissions SET status = ?, reviewed_at = CURRENT_TIMESTAMP WHERE id = ? AND status = 'pending'",
                (status, submission_id))
            return result.rowcount == 1
