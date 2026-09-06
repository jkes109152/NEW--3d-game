import unittest
from air_defense.progression import level_for, transact
from air_defense.catalog import upgrade_cap
from tests.fixtures.expansion import profile, request, operation_id

class EconomyTests(unittest.TestCase):
    def test_rewards_exact_floor(self):
        self.assertEqual([level_for(*a).reward for a in [(1,1,2),(2,5,2),(3,7,3)]],[125,490,1027])
    def test_player_upgrade_prices_caps_and_tower_gate(self):
        p=profile(coins=100000)
        self.assertEqual(transact(p,operation_id(99),request(p,'purchase_turret',turret_id='T01'))['reason'],'locked')
        for i,cost in enumerate((250,500,750,1000,1250)):
            before=p['coins'];self.assertEqual(transact(p,operation_id(i),request(p,'upgrade_player',upgrade_id='max_hp'))['result_code'],'applied')
            self.assertEqual(before-p['coins'],cost)
        self.assertEqual(transact(p,operation_id(6),request(p,'upgrade_player',upgrade_id='max_hp'))['reason'],'cap_reached')
        self.assertEqual([upgrade_cap(r) for r in (0,1,5,10)],[5,6,10,10])
    def test_rebirth_clears_upgrades_and_requires_increasing_threshold(self):
        p=profile(coins=1500);p['rebirth_available']=True
        transact(p,operation_id(),request(p,'upgrade_player',upgrade_id='max_hp'))
        self.assertEqual(transact(p,operation_id(2),request(p,'rebirth'))['result_code'],'applied')
        self.assertEqual((p['coins'],p['rebirth_count'],p['player_upgrades']['max_hp']),(0,1,0))
        self.assertFalse(p['rebirth_available']);p.update(coins=1999,rebirth_available=True)
        self.assertEqual(transact(p,operation_id(3),request(p,'rebirth'))['reason'],'insufficient_coins')
