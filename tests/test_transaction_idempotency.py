import unittest
from copy import deepcopy
from air_defense.progression import transact
from tests.fixtures.expansion import profile, request, operation_id

class TransactionIdempotencyTests(unittest.TestCase):
    def test_purchase_reward_rebirth_same_and_conflicting_fingerprints(self):
        for kind,fields in [('upgrade_player',dict(upgrade_id='max_hp')),('reward',dict(a=1,b=1,A=2)),('rebirth',{})]:
            p=profile(coins=5000);p['rebirth_available']=True;req=request(p,kind,**fields)
            first=transact(p,operation_id(),req);expected=deepcopy(p)
            replay=transact(p,operation_id(),req)
            self.assertEqual(replay,{**first,'replayed':True});self.assertEqual(p,expected)
            self.assertEqual(transact(p,operation_id(),request(p,'purchase_armor',armor_id='A01'))['result_code'],'operation_conflict')
            self.assertEqual(p,expected)
