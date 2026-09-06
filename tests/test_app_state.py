import unittest
from tempfile import TemporaryDirectory
from air_defense.state import AppState
from air_defense.save_data import SlotRepository

class AppStateTests(unittest.TestCase):
    def test_flow_restart_and_manual_start(self):
        with TemporaryDirectory() as root:
            repo=SlotRepository(root); app=AppState(repo)
            self.assertEqual(app.screen,'slot_select'); self.assertIsNone(app.start())
            app.select_slot(1); self.assertEqual(app.screen,'profile_menu')
            b=app.start(); self.assertEqual(b.level.level_id,'1-1')
            for a in b.aircraft.values(): a.hp=0; a.status='destroyed'
            b.check_outcome(); app.settle()
            self.assertEqual(app.cursor,(1,2)); self.assertEqual(app.screen,'result_success')
            app.show_menu(); self.assertIsNone(app.battle)
            reopened=AppState(repo); reopened.select_slot(1)
            self.assertEqual(reopened.cursor,(1,1)); self.assertEqual(reopened.profile['coins'],125)
