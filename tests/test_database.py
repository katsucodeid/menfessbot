import os
import tempfile
import unittest
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

if __name__ == "__main__":
    unittest.main()
