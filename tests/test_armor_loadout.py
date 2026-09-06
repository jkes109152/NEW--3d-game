import unittest
from copy import deepcopy
from air_defense.loadout import resolve_player_stats,validate_loadout
from air_defense.progression import transact
from tests.fixtures.expansion import profile,request,operation_id

class ArmorLoadoutTests(unittest.TestCase):
    def test_six_fixed_armors_no_stacking_and_no_armor(self):
        p=profile(coins=10000)
        expected=[(100,6,0,5,4),(100,5.4,3,5,2),(110,6,1,5,3),(90,7.2,0,5,2),(140,5.7,0,5,2),(100,6,0,2.5,2)]
        for i,row in enumerate(expected,1):
            aid=f'A{i:02}';req=request(p,'purchase_armor',armor_id=aid)
            self.assertEqual(transact(p,operation_id(i),req)['result_code'],'applied')
            self.assertEqual(transact(p,operation_id(100+i),req)['reason'],'already_owned')
            stats=resolve_player_stats(p,aid)
            for value,wanted in zip((stats.max_hp,stats.move_speed,stats.damage_reduction,stats.regen_delay,stats.regen_rate),row):self.assertAlmostEqual(value,wanted)
        self.assertEqual(resolve_player_stats(p).max_hp,100)
        d=deepcopy(p['confirmed_loadout']);d['armor_id']=['A01','A02'];self.assertEqual(validate_loadout(p,d),'not_owned')
    def test_armor_is_not_upgradable(self):
        p=profile(coins=9999)
        self.assertEqual(transact(p,operation_id(),request(p,'upgrade_armor',armor_id='A01'))['reason'],'invalid_request')
