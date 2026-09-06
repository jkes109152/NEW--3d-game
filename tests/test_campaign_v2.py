import unittest
from unittest.mock import patch
from air_defense.state import AppState
from air_defense.save_data import SlotRepository
from tests.fixtures.expansion import isolated_roots,start_prepared

class CampaignV2Tests(unittest.TestCase):
    def test_reward_failure_save_retries_identity_and_manual_cursor(self):
        with isolated_roots() as (root,_):
            app=AppState(SlotRepository(root));app.select_slot(1);b=start_prepared(app);b.phase='success'
            with patch('air_defense.save_data.os.replace',side_effect=OSError('fault')):app.settle()
            self.assertEqual(app.cursor,(1,1));self.assertEqual(app.profile['coins'],125);app.settle();self.assertEqual(app.profile['coins'],125)
            self.assertTrue(app.retry_save());self.assertEqual(app.cursor,(1,2));app.show_menu();self.assertIsNone(app.battle)
            old=b.attempt_id;b=start_prepared(app);self.assertNotEqual(b.attempt_id,old);b.fail('player');app.settle();app.show_menu();self.assertEqual(app.cursor,(1,2))
            b=start_prepared(app);self.assertEqual(b.level.level_id,'1-2');self.assertEqual(app.transaction('reward',old,a=1,b=1,A=2)['reason'],'phase')
    def test_first_nonempty_slot_and_draft_cancel_back(self):
        with isolated_roots() as (root,_):
            app=AppState(SlotRepository(root));app.select_slot(1);app.begin_preparation();app.next_preparation();app.back_preparation();self.assertEqual(app.screen,'prepare_armor')
            app.draft.loadout['weapon_slots']=[None,'W17',None,'W01',None];app.cancel_preparation();self.assertEqual(app.profile['confirmed_loadout']['weapon_slots'][0],'W01')
            app.begin_preparation();app.draft.loadout['weapon_slots']=[None,'W17',None,'W01',None]
            for _ in range(3):app.next_preparation()
            self.assertEqual(app.confirm_and_start().player.weapon_slot,2)
