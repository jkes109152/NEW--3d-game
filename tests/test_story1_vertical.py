import unittest
from tempfile import TemporaryDirectory
from air_defense.state import AppState, InputFrame
from air_defense.save_data import SlotRepository

class VerticalSliceTests(unittest.TestCase):
    def test_clear_normal_aircraft_and_dropped_soldiers_once(self):
        with TemporaryDirectory() as root:
            app=AppState(SlotRepository(root)); app.select_slot(1); b=app.start()
            b.damage_aircraft('air-0',1)
            for e in list(b.enemies.values()): b.damage_enemy(e.id,e.hp)
            b.advance(1/60,InputFrame()); app.settle(); app.settle()
            self.assertEqual(app.profile['coins'],125)
            self.assertEqual(len(app.profile['operation_history']),1)
            self.assertEqual(app.repository.load(1)['coins'],125)
