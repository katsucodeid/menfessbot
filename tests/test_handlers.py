import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from menfessbot.handlers import (
    help_command, membership_gate, moderate, privacy_command, receive_submission,
    role_for, valid_submission_hashtag,
)


class HashtagTests(unittest.TestCase):
    def setUp(self):
        self.allowed = ("#katsuboy", "#katsugirl", "#katsuask")

    def test_accepts_one_allowed_hashtag_case_insensitively(self):
        self.assertTrue(valid_submission_hashtag("#KatsuBoy Halo", self.allowed))

    def test_rejects_missing_hashtag(self):
        self.assertFalse(valid_submission_hashtag("Halo", self.allowed))

    def test_rejects_multiple_allowed_hashtags(self):
        self.assertFalse(valid_submission_hashtag("#katsuboy #katsugirl Halo", self.allowed))

    def test_rejects_unknown_hashtag(self):
        self.assertFalse(valid_submission_hashtag("#katsuadmin Halo", self.allowed))

    def test_rejects_extra_unknown_hashtag(self):
        self.assertFalse(valid_submission_hashtag("#katsuboy #lainnya Halo", self.allowed))


class RoleTests(unittest.TestCase):
    def test_role_precedence(self):
        settings = SimpleNamespace(developer_ids={1}, admin_ids={1, 2})
        self.assertEqual(role_for(1, settings), "Developer")
        self.assertEqual(role_for(2, settings), "Admin")
        self.assertEqual(role_for(3, settings), "Member")


class MembershipTests(unittest.IsolatedAsyncioTestCase):
    async def test_requires_both_group_and_channel(self):
        bot = SimpleNamespace(get_chat_member=AsyncMock(side_effect=[
            SimpleNamespace(status="member"), SimpleNamespace(status="administrator")
        ]))
        message = SimpleNamespace(reply_text=AsyncMock())
        update = SimpleNamespace(effective_user=SimpleNamespace(id=42), effective_message=message)
        settings = SimpleNamespace(required_group_id=-1001, required_channel_id=-1002,
                                   group_join_url="", channel_join_url="")
        context = SimpleNamespace(application=SimpleNamespace(bot_data={"settings": settings}), bot=bot)
        self.assertTrue(await membership_gate(update, context))
        self.assertEqual(bot.get_chat_member.await_count, 2)

    async def test_non_member_is_blocked(self):
        bot = SimpleNamespace(get_chat_member=AsyncMock(side_effect=[
            SimpleNamespace(status="left"), SimpleNamespace(status="member")
        ]))
        message = SimpleNamespace(reply_text=AsyncMock())
        update = SimpleNamespace(effective_user=SimpleNamespace(id=42), effective_message=message)
        settings = SimpleNamespace(required_group_id=-1001, required_channel_id=-1002,
                                   group_join_url="", channel_join_url="")
        context = SimpleNamespace(application=SimpleNamespace(bot_data={"settings": settings}), bot=bot)
        self.assertFalse(await membership_gate(update, context))
        message.reply_text.assert_awaited_once()


class HandlerTests(unittest.IsolatedAsyncioTestCase):
    def make_submission_context(self, *, audit_channel_id=700, allowed_hashtags=("#katsuboy",),
                                create_result=(7, None), admin_ids=frozenset({9}), developer_ids=frozenset()):
        store = Mock()
        store.create_submission.return_value = create_result
        store.get.return_value = {"created_at": "2026-11-17 10:00:00"}
        settings = SimpleNamespace(
            developer_ids=developer_ids, admin_ids=admin_ids, allowed_hashtags=allowed_hashtags,
            required_group_id=-1001, required_channel_id=-1002, audit_channel_id=audit_channel_id,
            submission_cooldown_seconds=60, submission_hourly_limit=5,
            submission_coin_cost=2, channel_id=-100500,
        )
        bot = SimpleNamespace(send_message=AsyncMock(), copy_message=AsyncMock())
        context = SimpleNamespace(application=SimpleNamespace(bot_data={
            "settings": settings, "store": store
        }), bot=bot)
        user = SimpleNamespace(id=42, username="tester", full_name="Test User")
        message = SimpleNamespace(
            chat=SimpleNamespace(type="private"), chat_id=42, message_id=200,
            text="#katsuboy Hello", caption=None, reply_text=AsyncMock()
        )
        update = SimpleNamespace(effective_message=message, effective_user=user)
        return update, message, context, store, bot

    async def test_privacy_discloses_data_and_retention_disabled(self):
        message = SimpleNamespace(reply_text=AsyncMock())
        update = SimpleNamespace(effective_message=message)
        context = SimpleNamespace(application=SimpleNamespace(bot_data={
            "settings": SimpleNamespace(retention_days=0)
        }))
        await privacy_command(update, context)
        response = message.reply_text.await_args.args[0]
        self.assertIn("Privasi MenfessBot\n", response)
        self.assertIn("Pembersihan otomatis", response)
        self.assertIn("pending", response)
        self.assertIn("moderator", response)

    async def test_privacy_reports_configured_retention(self):
        message = SimpleNamespace(reply_text=AsyncMock())
        update = SimpleNamespace(effective_message=message)
        context = SimpleNamespace(application=SimpleNamespace(bot_data={
            "settings": SimpleNamespace(retention_days=30)
        }))
        await privacy_command(update, context)
        self.assertIn("30 hari", message.reply_text.await_args.args[0])

    async def test_help_lists_configured_hashtags(self):
        message = SimpleNamespace(reply_text=AsyncMock())
        update = SimpleNamespace(effective_message=message)
        context = SimpleNamespace(application=SimpleNamespace(bot_data={
            "settings": SimpleNamespace(allowed_hashtags=("#katsuboy", "#katsuask"))
        }))
        await help_command(update, context)
        response = message.reply_text.await_args.args[0]
        self.assertIn("#katsuboy", response)
        self.assertIn("#katsuask", response)

    async def test_missing_user_is_rejected_without_database_write(self):
        update, message, context, store, _ = self.make_submission_context()
        update.effective_user = None
        await receive_submission(update, context)
        store.create_submission.assert_not_called()
        self.assertIn("tanpa identitas", message.reply_text.await_args.args[0])

    async def test_rate_limited_submission_is_not_sent_to_moderators(self):
        update, message, context, store, bot = self.make_submission_context(create_result=(None, "rate_limit"))
        with patch("menfessbot.handlers.membership_gate", new=AsyncMock(return_value=True)):
            await receive_submission(update, context)
        store.create_submission.assert_called_once()
        bot.send_message.assert_not_awaited()
        bot.copy_message.assert_not_awaited()
        self.assertIn("Batas pengiriman", message.reply_text.await_args.args[0])

    async def test_insufficient_coins_is_rejected(self):
        update, message, context, store, bot = self.make_submission_context(create_result=(None, "insufficient_coins"))
        with patch("menfessbot.handlers.membership_gate", new=AsyncMock(return_value=True)):
            await receive_submission(update, context)
        bot.send_message.assert_not_awaited()
        self.assertIn("Koin tidak cukup", message.reply_text.await_args.args[0])

    async def test_missing_or_multiple_hashtags_are_rejected_before_database_write(self):
        for content in ("Tanpa tag", "#katsuboy #katsuask ganda"):
            update, message, context, store, bot = self.make_submission_context()
            message.text = content
            with patch("menfessbot.handlers.membership_gate", new=AsyncMock(return_value=True)):
                await receive_submission(update, context)
            store.create_submission.assert_not_called()
            bot.send_message.assert_not_awaited()

    async def test_text_submission_audits_identity_and_notifies_moderator(self):
        update, message, context, store, bot = self.make_submission_context()
        with patch("menfessbot.handlers.membership_gate", new=AsyncMock(return_value=True)):
            await receive_submission(update, context)
        audit = next(call.args[1] for call in bot.send_message.await_args_list if call.args[0] == 700)
        self.assertIn("Telegram ID: 42", audit)
        self.assertIn("tester", audit)
        self.assertIn("Test User", audit)
        self.assertTrue(any(call.args[0] == 9 for call in bot.send_message.await_args_list))
        bot.copy_message.assert_awaited_once_with(9, 42, 200)

    async def test_caption_submission_uses_same_hashtag_validation(self):
        update, message, context, store, bot = self.make_submission_context()
        message.text = None
        message.caption = "Foto produk #katsuboy"
        with patch("menfessbot.handlers.membership_gate", new=AsyncMock(return_value=True)):
            await receive_submission(update, context)
        store.create_submission.assert_called_once()

    async def test_publication_uses_only_configured_destination_channel(self):
        _, _, context, store, bot = self.make_submission_context()
        callback = SimpleNamespace(
            from_user=SimpleNamespace(id=9), data="approve:7",
            answer=AsyncMock(), edit_message_text=AsyncMock()
        )
        store.claim.return_value = True
        store.get.return_value = {"source_chat_id": 42, "source_message_id": 200}
        store.set_status.return_value = True
        await moderate(SimpleNamespace(callback_query=callback), context)
        bot.copy_message.assert_awaited_once_with(-100500, 42, 200)
        store.set_status.assert_called_once_with(7, "approved")
        callback.edit_message_text.assert_awaited_with("Menfess #7: approved.")

    async def test_moderation_does_not_report_success_if_status_update_fails(self):
        _, _, context, store, _ = self.make_submission_context()
        callback = SimpleNamespace(
            from_user=SimpleNamespace(id=9), data="reject:7",
            answer=AsyncMock(), edit_message_text=AsyncMock()
        )
        store.claim.return_value = True
        store.get.return_value = {"source_chat_id": 42, "source_message_id": 200}
        store.set_status.return_value = False
        await moderate(SimpleNamespace(callback_query=callback), context)
        self.assertIn("status database gagal", callback.edit_message_text.await_args.args[0])
        store.release_claim.assert_called_once_with(7)

    async def test_non_moderator_cannot_moderate(self):
        _, _, context, store, _ = self.make_submission_context()
        callback = SimpleNamespace(
            from_user=SimpleNamespace(id=1234), data="approve:7",
            answer=AsyncMock(), edit_message_text=AsyncMock()
        )
        await moderate(SimpleNamespace(callback_query=callback), context)
        callback.answer.assert_awaited_once_with("Akses ditolak.", show_alert=True)
        store.claim.assert_not_called()


if __name__ == "__main__":
    unittest.main()
