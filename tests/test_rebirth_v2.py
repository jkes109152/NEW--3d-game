import unittest
from copy import deepcopy
from air_defense.progression import transact
from air_defense.ui import Settings
from air_defense.save_data import SlotRepository
from tests.test_save_v2_matrix import rich_profile
from tests.fixtures.expansion import request,operation_id,isolated_roots

class RebirthTests(unittest.TestCase):
    def test_full_clear_history_settings_and_past_round_replays(self):
        p=rich_profile();old_req=request(p,'upgrade_weapon',weapon_id='W17',upgrade_id='damage')
        first=transact(p,operation_id(),old_req);p['player_upgrades']['max_hp']=3
        p['confirmed_loadout'].update(armor_id='A01',deployments=[dict(instance_id=p['owned_turrets'][0]['instance_id'],x=40,z=100)])
        old=deepcopy(p['operation_history']);rebirth=request(p,'rebirth')
        self.assertEqual(transact(p,operation_id(2),rebirth)['result_code'],'applied')
        self.assertEqual((p['coins'],p['rebirth_count'],p['player_upgrades']['max_hp']),(0,2,0))
        self.assertEqual(p['owned_armors'],[]);self.assertEqual(p['owned_turrets'],[]);self.assertEqual(list(p['owned_weapons']),['W01','W17','W03'])
        for w in p['owned_weapons'].values():
            self.assertEqual(sum(w['upgrade_levels'].values()),0);self.assertEqual(w['owned_attachments'],[]);self.assertEqual(w['owned_colors'],['original']);self.assertEqual(w['owned_patterns'],['plain'])
        self.assertEqual(p['operation_history'][:1],old)
        self.assertEqual(transact(p,operation_id(),old_req),{**first,'replayed':True});self.assertEqual(p['owned_weapons']['W17']['upgrade_levels']['damage'],0)
        self.assertEqual(transact(p,operation_id(3),old_req)['reason'],'stale_round');revision=p['profile_revision'];transact(p,operation_id(3),old_req);self.assertEqual(p['profile_revision'],revision)
        with isolated_roots() as (root,_):
            settings=Settings(sensitivity=2,quality='low');settings.save(root);before=(root/'settings.json').read_bytes();repo=SlotRepository(root);repo.save(1,p)
            self.assertEqual((root/'settings.json').read_bytes(),before);self.assertEqual(Settings.load(root).sensitivity,2)
