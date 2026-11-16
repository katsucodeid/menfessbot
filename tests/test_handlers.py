import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from menfessbot.handlers import privacy_command, receive_submission


class HandlerTests(unittest.IsolatedAsyncioTestCase):
    def make_update(self, user_id=42):
        message = SimpleNamespace(
            chat_id=100, message_id=200, reply_text=AsyncMock()
        )
        return SimpleNamespace(
            effective_message=message,
            effective_user=SimpleNamespace(id=user_id) if user_id is not None else None,
        ), message

    async def test_privacy_command_explains_stored_data_and_pending_retention(self):
        update, message = self.make_update()
        await privacy_command(update, SimpleNamespace())
        text = message.reply_text.await_args.args[0]
        self.assertIn("ID pengguna", text)
        self.assertIn("tidak dihapus otomatis", text)
        self.assertIn("moderator", text)

    async def test_rate_limited_submission_is_not_sent_to_moderators(self):
        update, message = self.make_update()
        store = Mock()
        store.add_with_limits.return_value = None
        bot = SimpleNamespace(send_message=AsyncMock(), copy_message=AsyncMock())
        settings = SimpleNamespace(submission_cooldown_seconds=60, submission_hourly_limit=5)
        context = SimpleNamespace(application=SimpleNamespace(bot_data={
            "store": store, "settings": settings, "admin_ids": {9}
        }), bot=bot)
        await receive_submission(update, context)
        store.add_with_limits.assert_called_once()
        bot.send_message.assert_not_awaited()
        bot.copy_message.assert_not_awaited()
        self.assertIn("Batas pengiriman", message.reply_text.await_args.args[0])

    async def test_missing_user_is_rejected(self):
        update, message = self.make_update(user_id=None)
        store = Mock()
        context = SimpleNamespace(application=SimpleNamespace(bot_data={"store": store}))
        await receive_submission(update, context)
        store.add_with_limits.assert_not_called()
        self.assertIn("tanpa identitas", message.reply_text.await_args.args[0])

    async def test_accepted_submission_notifies_moderator(self):
        update, message = self.make_update()
        store = Mock()
        store.add_with_limits.return_value = 7
        bot = SimpleNamespace(send_message=AsyncMock(), copy_message=AsyncMock())
        settings = SimpleNamespace(submission_cooldown_seconds=60, submission_hourly_limit=5)
        context = SimpleNamespace(application=SimpleNamespace(bot_data={
            "store": store, "settings": settings, "admin_ids": {9}
        }), bot=bot)
        await receive_submission(update, context)
        bot.send_message.assert_awaited_once()
        bot.copy_message.assert_awaited_once_with(9, 100, 200)
        self.assertIn("diterima", message.reply_text.await_args.args[0])


if __name__ == "__main__":
    unittest.main()
