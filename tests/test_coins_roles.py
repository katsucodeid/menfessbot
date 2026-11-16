import os,tempfile,unittest
from menfessbot.database import SubmissionStore
class EconomyTests(unittest.TestCase):
 def setUp(self): self.tmp=tempfile.TemporaryDirectory(); self.store=SubmissionStore(os.path.join(self.tmp.name,'db.sqlite'))
 def tearDown(self): self.tmp.cleanup()
 def test_grant_transfer_ledger(self):
  self.assertTrue(self.store.change_coins(10,20,99,'bonus','grant')); self.assertTrue(self.store.transfer_coins(10,11,7)); self.assertEqual(self.store.balance(10),13); self.assertEqual(self.store.balance(11),7)
 def test_no_overdraft(self): self.assertFalse(self.store.transfer_coins(10,11,1))
 def test_paid_submission(self):
  self.store.change_coins(10,5,99,'seed','grant'); sid,error=self.store.create_submission(1,1,10,cooldown_seconds=0,hourly_limit=5,coin_cost=2); self.assertIsNone(error); self.assertEqual(self.store.balance(10),3)
 def test_developer_unlimited(self):
  sid,error=self.store.create_submission(1,1,99,cooldown_seconds=0,hourly_limit=5,coin_cost=500,unlimited=True); self.assertIsNone(error); self.assertEqual(self.store.balance(99),0)
 def test_insufficient_coins(self):
  sid,error=self.store.create_submission(1,1,10,cooldown_seconds=0,hourly_limit=5,coin_cost=1); self.assertIsNone(sid); self.assertEqual(error,'insufficient_coins')
 def test_rejection_refund_once(self):
  self.store.change_coins(10,5,99,'seed','grant'); sid,_=self.store.create_submission(1,1,10,cooldown_seconds=0,hourly_limit=5,coin_cost=2); self.assertEqual(self.store.balance(10),3); self.assertTrue(self.store.set_status(sid,'rejected')); self.assertFalse(self.store.set_status(sid,'rejected')); self.assertEqual(self.store.balance(10),5); self.assertEqual(self.store.transactions(10)[0]['transaction_type'],'refund')
if __name__=='__main__': unittest.main()
