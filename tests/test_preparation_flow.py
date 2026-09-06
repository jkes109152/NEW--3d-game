import unittest
from unittest.mock import patch
from air_defense.state import AppState
from air_defense.save_data import SlotRepository
from tests.fixtures.expansion import isolated_roots
class PreparationFlowTests(unittest.TestCase):
    def test_save_error_never_starts_battle(self):
        with isolated_roots() as (root,_):
            app=AppState(SlotRepository(root));app.select_slot(1);app.begin_preparation()
            for _ in range(3):self.assertIsNone(app.next_preparation())
            with patch('air_defense.save_data.os.replace',side_effect=OSError('fault')):self.assertIsNone(app.confirm_and_start())
            self.assertEqual(app.screen,'save_error');self.assertIsNone(app.battle)
            self.assertTrue(app.retry_save());self.assertEqual(app.screen,'prepare_confirm');self.assertIsNone(app.battle)
            b=app.confirm_and_start();self.assertIsNotNone(b)
            self.assertEqual(app.profile['coins'],0)
    def test_purchase_failure_retains_complete_candidate(self):
        with isolated_roots() as (root,_):
            app=AppState(SlotRepository(root));app.select_slot(1);app.profile['coins']=1000;app.repository.save(1,app.profile)
            with patch('air_defense.save_data.os.replace',side_effect=OSError('fault')):app.purchase('max_hp','1'*32)
            self.assertEqual(app.profile['coins'],750);self.assertEqual(app.repository.load(1)['coins'],1000)
            self.assertEqual(app.purchase('max_hp'),'phase');self.assertTrue(app.retry_save())
            self.assertEqual(app.repository.load(1)['player_upgrades']['max_hp'],1)
