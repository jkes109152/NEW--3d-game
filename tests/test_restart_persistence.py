import unittest
from tempfile import TemporaryDirectory
from air_defense.save_data import SlotRepository
from air_defense.state import AppState
from tests.fixtures.expansion import start_prepared

class RestartPersistenceTests(unittest.TestCase):
    def test_only_permanent_state_survives(self):
        with TemporaryDirectory() as root:
            repo=SlotRepository(root);app=AppState(repo);app.select_slot(1);app.profile['coins']=1000
            self.assertEqual(app.transaction('purchase_weapon',weapon_id='W19')['result_code'],'applied')
            app.begin_preparation();app.set_draft_slot(4,'W19')
            for _ in range(3):app.next_preparation()
            b=app.confirm_and_start();b.player.hp=20;b.select_weapon(4);b.fire()
            reopened=AppState(SlotRepository(root));reopened.select_slot(1);fresh=start_prepared(reopened)
            self.assertEqual(reopened.profile['coins'],500)
            self.assertEqual((fresh.player.hp,fresh.runtime['W19'].quota_remaining,fresh.runtime['W19'].next_shot_at),(100,3,0))
            self.assertEqual(fresh.lock.progress,{});self.assertEqual(fresh.missiles,{});self.assertEqual(fresh.rockets,{})
