import unittest
from copy import deepcopy
from air_defense.catalog import WEAPONS, UPGRADE_PRICES, applicable_upgrade
from air_defense.progression import transact
from tests.fixtures.expansion import profile, request, operation_id

class ShopTests(unittest.TestCase):
    def test_twenty_weapons_exact_cost_and_repurchase(self):
        expected=[0,750,0,300,450,350,450,550,650,700,250,350,400,500,400,650,0,800,500,850]
        p=profile(coins=100000)
        for i,(wid,w) in enumerate(WEAPONS.items()):
            self.assertEqual(w.price,expected[i]);before=p['coins']
            r=transact(p,operation_id(i),request(p,'purchase_weapon',weapon_id=wid))
            self.assertEqual(r['reason'],'already_owned' if w.price==0 else 'ok')
            self.assertEqual(before-p['coins'],w.price)
            self.assertEqual(transact(p,operation_id(i+100),request(p,'purchase_weapon',weapon_id=wid))['reason'],'already_owned')
    def test_upgrade_isolation_caps_and_ownership(self):
        p=profile(coins=100000);transact(p,operation_id(),request(p,'purchase_weapon',weapon_id='W18'));other=deepcopy(p['owned_weapons']['W18'])
        for i in range(5):self.assertEqual(transact(p,operation_id(10+i),request(p,'upgrade_weapon',weapon_id='W17',upgrade_id='range'))['coins_delta'],-200*(i+1))
        self.assertEqual(p['owned_weapons']['W18'],other)
        for wid,upgrade,reason in [('W17','range','cap_reached'),('W03','range','incompatible'),('W02','damage','not_owned')]:
            self.assertEqual(transact(p,operation_id(100+len(p['operation_history'])),request(p,'upgrade_weapon',weapon_id=wid,upgrade_id=upgrade))['reason'],reason)
    def test_insufficient_funds_does_not_grant_item(self):
        p=profile(coins=299);r=transact(p,operation_id(),request(p,'purchase_weapon',weapon_id='W04'))
        self.assertEqual(r['reason'],'insufficient_coins');self.assertNotIn('W04',p['owned_weapons']);self.assertEqual(p['coins'],299)
