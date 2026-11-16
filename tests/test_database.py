import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from menfessbot.database import SubmissionStore


class SubmissionStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = SubmissionStore(os.path.join(self.temp.name, "test.db"))

    def tearDown(self):
        self.temp.cleanup()

    def test_add_and_get(self):
        sid = self.store.add(123, 456, 789)
        row = self.store.get(sid)
        self.assertEqual(row["source_chat_id"], 123)
        self.assertEqual(row["source_message_id"], 456)
        self.assertEqual(row["sender_user_id"], 789)
        self.assertEqual(row["status"], "pending")

    def test_status_is_one_way(self):
        sid = self.store.add(123, 456, None)
        self.assertTrue(self.store.set_status(sid, "approved"))
        self.assertFalse(self.store.set_status(sid, "rejected"))

    def test_invalid_status(self):
        sid = self.store.add(123, 456, None)
        with self.assertRaises(ValueError):
            self.store.set_status(sid, "published")

    def test_only_one_moderator_can_claim_submission(self):
        sid = self.store.add(123, 456, None)
        self.assertTrue(self.store.claim(sid))
        self.assertFalse(self.store.claim(sid))

    def test_releasing_claim_allows_retry(self):
        sid = self.store.add(123, 456, None)
        self.assertTrue(self.store.claim(sid))
        self.store.release_claim(sid)
        self.assertTrue(self.store.claim(sid))

    def test_final_status_removes_claim_and_prevents_reclaim(self):
        sid = self.store.add(123, 456, None)
        self.assertTrue(self.store.claim(sid))
        self.assertTrue(self.store.set_status(sid, "rejected"))
        self.assertFalse(self.store.claim(sid))
        self.assertEqual(self.store.get(sid)["status"], "rejected")

    def test_cooldown_blocks_rapid_submission(self):
        now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        first = self.store.add_with_limits(1, 1, 10, cooldown_seconds=60, hourly_limit=5, now=now)
        second = self.store.add_with_limits(1, 2, 10, cooldown_seconds=60, hourly_limit=5, now=now + timedelta(seconds=30))
        self.assertIsNotNone(first)
        self.assertIsNone(second)

    def test_cooldown_allows_after_interval(self):
        now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        self.store.add_with_limits(1, 1, 10, cooldown_seconds=60, hourly_limit=5, now=now)
        second = self.store.add_with_limits(1, 2, 10, cooldown_seconds=60, hourly_limit=5, now=now + timedelta(seconds=61))
        self.assertIsNotNone(second)

    def test_hourly_limit_blocks_sixth_submission(self):
        now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        for index in range(5):
            sid = self.store.add_with_limits(1, index + 1, 10, cooldown_seconds=0, hourly_limit=5,
                                             now=now + timedelta(minutes=index * 2))
            self.assertIsNotNone(sid)
        blocked = self.store.add_with_limits(1, 99, 10, cooldown_seconds=0, hourly_limit=5,
                                             now=now + timedelta(minutes=11))
        self.assertIsNone(blocked)

    def test_rate_limit_is_per_user(self):
        now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        self.store.add_with_limits(1, 1, 10, cooldown_seconds=60, hourly_limit=1, now=now)
        other = self.store.add_with_limits(1, 2, 11, cooldown_seconds=60, hourly_limit=1, now=now)
        self.assertIsNotNone(other)

    def test_retention_removes_only_old_reviewed_rows(self):
        now = datetime(2026, 2, 1, tzinfo=timezone.utc)
        old_pending = self.store.add(1, 1, 10)
        old_approved = self.store.add(1, 2, 10)
        self.store.set_status(old_approved, "approved")
        # Set deterministic historical timestamps for the test.
        import sqlite3
        with self.store._connect() as db:
            db.execute("UPDATE submissions SET created_at = ?, reviewed_at = ? WHERE id = ?",
                       ((now - timedelta(days=31)).strftime("%Y-%m-%d %H:%M:%S"),
                        (now - timedelta(days=31)).strftime("%Y-%m-%d %H:%M:%S"), old_approved))
            db.execute("UPDATE submissions SET created_at = ? WHERE id = ?",
                       ((now - timedelta(days=31)).strftime("%Y-%m-%d %H:%M:%S"), old_pending))
        self.assertEqual(self.store.prune_reviewed(30, now=now), 1)
        self.assertIsNotNone(self.store.get(old_pending))
        self.assertIsNone(self.store.get(old_approved))


if __name__ == "__main__":
    unittest.main()
