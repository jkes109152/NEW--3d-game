import unittest,json,subprocess,sys
from pathlib import Path
from copy import deepcopy
from unittest.mock import patch
from air_defense.save_data import SlotRepository,validate_profile
from air_defense.state import AppState
from tests.fixtures.expansion import profile,owned_weapon,request,operation_id,isolated_roots,start_prepared


def rich_profile():
    p=profile(coins=100000,rebirth_count=1);p['rebirth_available']=True;p['owned_armors']=['A01'];w=p['owned_weapons']['W17']
    w['owned_attachments']=['zoom_scope'];w['owned_colors'].append('mint');w['owned_patterns'].append('dots')
    p['owned_turrets']=[dict(instance_id='turret-'+operation_id(99),turret_id='T01')]
    return p


class SaveMatrixTests(unittest.TestCase):
    def test_twelve_transactions_replace_failure_complete_candidate_retry(self):
        cases=[('purchase_weapon',dict(weapon_id='W06')),('purchase_armor',dict(armor_id='A02')),('purchase_turret',dict(turret_id='T02')),('upgrade_player',dict(upgrade_id='max_hp')),('upgrade_weapon',dict(weapon_id='W17',upgrade_id='damage')),('purchase_attachment',dict(weapon_id='W17',attachment_id='heavy_barrel')),('purchase_cosmetic',dict(weapon_id='W17',cosmetic_kind='color',cosmetic_id='strawberry')),('customize_weapon',dict(weapon_id='W17',selected_attachments=dict(optic='zoom_scope',barrel=None,feed=None),selected_color='mint',selected_pattern='dots')),('confirm_loadout',{}),('reward',{}),('failure',{}),('rebirth',{})]
        for i,(kind,fields) in enumerate(cases):
            with self.subTest(kind=kind),isolated_roots() as (root,old):
                repo=SlotRepository(root);repo.save(1,rich_profile());app=AppState(repo);app.select_slot(1)
                op=operation_id(i+1)
                if kind=='confirm_loadout':
                    app.begin_preparation()
                    for _ in range(3):app.next_preparation()
                    fields=dict(loadout=deepcopy(app.draft.loadout))
                if kind in ('reward','failure'):
                    b=start_prepared(app);b.phase='success' if kind=='reward' else 'failure';op=b.attempt_id;fields=dict(a=1,b=1,A=3)
                before=repo.path(1).read_bytes()
                with patch('air_defense.save_data.os.replace',side_effect=PermissionError('fault')):result=app.transaction(kind,op,**fields)
                self.assertEqual(result['result_code'],'failed_retryable');self.assertEqual(repo.path(1).read_bytes(),before)
                candidate=deepcopy(app.pending_save.candidate_profile);self.assertEqual(app.transaction('purchase_weapon',weapon_id='W04')['reason'],'phase')
                with patch('air_defense.progression.transact',side_effect=AssertionError('重試不應重算交易')):self.assertTrue(app.retry_save())
                self.assertEqual(repo.load(1),candidate)
                replay=repo.transaction(1,candidate,op,request(rich_profile(),kind,**fields))
                self.assertTrue(replay['replayed']);self.assertEqual(repo.load(1),candidate)
    def test_all_catalog_items_five_slots_and_legacy_bytes_mtime(self):
        from air_defense.catalog import WEAPONS,ARMORS,TURRETS,ATTACHMENTS
        from air_defense.progression import transact
        with isolated_roots() as (root,old):
            old.mkdir();legacy=old/'slot-1.json';legacy.write_bytes(b'{"schema_version":1}');stamp=legacy.stat().st_mtime_ns
            repo=SlotRepository(root)
            for slot in range(1,6):
                p=profile(coins=100000,rebirth_count=6);p['profile_id']=operation_id(1000+slot)
                p['owned_weapons']={k:owned_weapon() for k in WEAPONS};p['owned_armors']=list(ARMORS)
                for wid,w in p['owned_weapons'].items():
                    w['owned_attachments']=[a for a,d in ATTACHMENTS.items() if wid in d.applicable_weapons];w['owned_colors']=['original','mint'];w['selected_color']='mint';w['owned_patterns']=['plain','stars'];w['selected_pattern']='stars'
                repo.save(slot,p);self.assertEqual(repo.load(slot),validate_profile(p))
            self.assertEqual(legacy.read_bytes(),b'{"schema_version":1}');self.assertEqual(legacy.stat().st_mtime_ns,stamp)
    def test_process_termination_before_and_after_replace(self):
        with isolated_roots() as (root,_):
            repo=SlotRepository(root);repo.save(1,profile(coins=10));path=repo.path(1)
            script="import json,os,sys;from pathlib import Path;from air_defense.save_data import atomic_json;p=Path(sys.argv[1]);d=json.loads(p.read_text());d['coins']=20;real=os.replace;os.replace=lambda *a:os._exit(91) if sys.argv[2]=='before' else (real(*a),os._exit(92));atomic_json(p,d)"
            for mode,coins,code in [('before',10,91),('after',20,92)]:
                r=subprocess.run([sys.executable,'-c',script,str(path),mode],capture_output=True)
                self.assertEqual(r.returncode,code);self.assertEqual(repo.load(1)['coins'],coins)
