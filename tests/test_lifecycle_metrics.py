import unittest
from tests.fixtures import battle
from air_defense.state import InputFrame

class LifecycleMetricsTests(unittest.TestCase):
    def test_ten_teardowns_remove_all_active_rule_objects(self):
        for _ in range(10):
            b=battle(); b.damage_aircraft(list(b.aircraft)[0],1); b.advance(.01,InputFrame()); b.teardown()
            self.assertTrue(all(value==0 for value in b.metrics().values()))
            self.assertEqual(b.events,[]); self.assertEqual(b.pending_commands,[])
