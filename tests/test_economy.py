import unittest
from air_defense.progression import *

class EconomyTests(unittest.TestCase):
    def test_rewards_exact_floor(self):
        self.assertEqual(level_for(1,1,2).reward,125)
        self.assertEqual(level_for(2,5,2).reward,490)
        self.assertEqual(level_for(3,7,3).reward,1027)

    def test_all_ten_prices_caps_and_prerequisite(self):
        p=new_profile(); p['coins']=1000000
        self.assertEqual(purchase_error(p,'auto_defense_capacity'),'prerequisite_missing')
        for key,_,base,_ in UPGRADES:
            with self.subTest(key=key):
                count=caps(0).get(key,1)
                for level in range(count):
                    self.assertEqual(price(p,key),base*(level+1))
                    before=p['coins']
                    self.assertEqual(transact(p,f'{key}-{level}',{'kind':'purchase','upgrade_id':key}),'applied')
                    self.assertEqual(before-p['coins'],base*(level+1))
                self.assertEqual(purchase_error(p,key),'maxed')
        poor=new_profile()
        self.assertEqual(purchase_error(poor,'max_hp'),'insufficient_coins')

    def test_rebirth_fee_increases_preserves_permanent_and_zeroes_all_coins(self):
        p=new_profile(); p.update(coins=1500,rebirth_available=True)
        transact(p,'buy',{'kind':'purchase','upgrade_id':'max_hp'})
        transact(p,'r',{'kind':'rebirth'})
        self.assertEqual((p['coins'],p['rebirth_count'],p['max_aircraft_count']),(0,1,3))
        self.assertEqual(p['upgrade_levels']['max_hp'],1)
        self.assertFalse(p['rebirth_available']); self.assertEqual(p['upgrade_caps']['max_hp'],6)
        p.update(coins=1999,rebirth_available=True)
        self.assertEqual(transact(p,'r2',{'kind':'rebirth'}),'insufficient_coins')
