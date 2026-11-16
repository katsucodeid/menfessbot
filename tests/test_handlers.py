import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock
from menfessbot.handlers import role_for,membership_gate,valid_submission_hashtag
class HashtagTests(unittest.TestCase):
 def setUp(self):
  self.allowed=("#katsuboy","#katsugirl","#katsuask")
 def test_accepts_one_allowed_hashtag(self):
  self.assertTrue(valid_submission_hashtag("#KatsuBoy Halo semuanya",self.allowed))
 def test_rejects_missing_hashtag(self):
  self.assertFalse(valid_submission_hashtag("Halo semuanya",self.allowed))
 def test_rejects_multiple_allowed_hashtags(self):
  self.assertFalse(valid_submission_hashtag("#katsuboy #katsugirl Halo",self.allowed))
 def test_rejects_unconfigured_hashtag(self):
  self.assertFalse(valid_submission_hashtag("#katsuadmin Halo",self.allowed))
 def test_rejects_extra_unconfigured_hashtag(self):
  self.assertFalse(valid_submission_hashtag("#katsuboy #lainnya Halo",self.allowed))
class RoleTests(unittest.TestCase):
 def test_precedence(self):
  s=SimpleNamespace(developer_ids={1},admin_ids={1,2}); self.assertEqual(role_for(1,s),'Developer'); self.assertEqual(role_for(2,s),'Admin'); self.assertEqual(role_for(3,s),'Member')
class MembershipTests(unittest.IsolatedAsyncioTestCase):
 async def test_join_both(self):
  bot=SimpleNamespace(get_chat_member=AsyncMock(side_effect=[SimpleNamespace(status='member'),SimpleNamespace(status='administrator')])); msg=SimpleNamespace(reply_text=AsyncMock()); update=SimpleNamespace(effective_user=SimpleNamespace(id=42),effective_message=msg); s=SimpleNamespace(required_group_id=-1001,required_channel_id=-1002,group_join_url='',channel_join_url=''); ctx=SimpleNamespace(application=SimpleNamespace(bot_data={'settings':s}),bot=bot); self.assertTrue(await membership_gate(update,ctx)); self.assertEqual(bot.get_chat_member.await_count,2)
 async def test_not_joined_blocks(self):
  bot=SimpleNamespace(get_chat_member=AsyncMock(side_effect=[SimpleNamespace(status='left'),SimpleNamespace(status='member')])); msg=SimpleNamespace(reply_text=AsyncMock()); update=SimpleNamespace(effective_user=SimpleNamespace(id=42),effective_message=msg); s=SimpleNamespace(required_group_id=-1001,required_channel_id=-1002,group_join_url='',channel_join_url=''); ctx=SimpleNamespace(application=SimpleNamespace(bot_data={'settings':s}),bot=bot); self.assertFalse(await membership_gate(update,ctx)); msg.reply_text.assert_awaited_once()
if __name__=='__main__': unittest.main()
