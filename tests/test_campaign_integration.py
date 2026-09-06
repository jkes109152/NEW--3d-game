import unittest
from tempfile import TemporaryDirectory
from air_defense.state import AppState
from air_defense.save_data import SlotRepository
from air_defense.progression import campaign

class CampaignIntegrationTests(unittest.TestCase):
    def test_seven_stages_upgrade_failure_rebirth(self):
        with TemporaryDirectory() as root:
            app=AppState(SlotRepository(root)); app.select_slot(1)
            expected=0
            for level in campaign(2):
                b=app.start(); self.assertEqual(b.level.level_id,level.level_id)
                for a in b.aircraft.values(): a.status='destroyed'; a.hp=0
                b.check_outcome(); app.settle(); expected+=level.reward
                app.show_menu()
            self.assertEqual(app.profile['coins'],expected)
            self.assertEqual(app.purchase('max_hp'),'applied')
            b=app.start(); b.fail('player'); app.settle(); app.show_menu()
            self.assertEqual(app.profile['coins'],expected-250)
            self.assertEqual(app.rebirth(),'applied')
            self.assertEqual((app.profile['max_aircraft_count'],app.profile['coins'],app.cursor),(3,0,(1,1)))
            self.assertEqual(app.start().player.max_hp,110)
