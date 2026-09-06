import unittest
from copy import deepcopy
from air_defense.progression import new_profile, transact

class TransactionIdempotencyTests(unittest.TestCase):
    def test_purchase_reward_rebirth_same_and_conflicting_fingerprints(self):
        for request in ({'kind':'purchase','upgrade_id':'max_hp'},{'kind':'reward','a':1,'b':1,'A':2},{'kind':'rebirth'}):
            with self.subTest(request=request):
                p=new_profile(); p.update(coins=5000,rebirth_available=True)
                first=transact(p,'op',request); expected=deepcopy(p)
                self.assertEqual(transact(p,'op',request),first); self.assertEqual(p,expected)
                self.assertEqual(transact(p,'op',{'kind':'save'}),'operation_conflict'); self.assertEqual(p,expected)
