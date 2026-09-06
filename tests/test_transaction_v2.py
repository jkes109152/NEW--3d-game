import unittest
from copy import deepcopy
from air_defense.progression import transact
from tests.fixtures.expansion import profile, request, operation_id
class TransactionV2Tests(unittest.TestCase):
    def test_purchase_replay_and_conflict(self):
        p=profile(1000);req=request(p,'purchase_weapon',weapon_id='W06');op=operation_id()
        result=transact(p,op,req)
        self.assertEqual(result['result_code'],'applied');self.assertEqual(p['coins'],650)
        same=deepcopy(p);self.assertTrue(transact(p,op,req)['replayed']);self.assertEqual(p,same)
        self.assertEqual(transact(p,op,request(p,'purchase_weapon',weapon_id='W07'))['result_code'],'operation_conflict');self.assertEqual(p,same)
    def test_rejected_requests(self):
        p=profile();r=transact(p,operation_id(),request(p,'purchase_weapon',weapon_id='W06'))
        self.assertEqual(r['reason'],'insufficient_coins');self.assertEqual(p['profile_revision'],1)
        for i,kwargs in enumerate([{'profile_id':'2'*32},{'rebirth_count':1},{'price':0}],2):
            req=request(p,'purchase_weapon',weapon_id='W06');req.update(kwargs)
            transact(p,operation_id(i),req)
        self.assertEqual(p['profile_revision'],1)
