import unittest
from air_defense.progression import difficulty_for,level_for
from air_defense.state import BattleState
from tests.fixtures.expansion import profile

class DifficultyTests(unittest.TestCase):
    def test_factors_ceil_cap_and_baseline(self):
        d=difficulty_for(level_for(1,1,2));self.assertEqual([d.hp(1,True),d.hp(3),d.hp(10)],[1,3,10])
        d=difficulty_for(level_for(2,5,2));self.assertEqual([d.hp(1,True),d.hp(5,True),d.hp(3),d.hp(10)],[2,7,5,15])
        self.assertAlmostEqual(d.speed_factor,1.075);self.assertAlmostEqual(d.turn_factor,1.08)
        d=difficulty_for(level_for(19,39,19));self.assertEqual([d.hp(1,True),d.hp(3),d.speed_factor,d.turn_factor],[4,12,1.35,1.5])
    def test_aircraft_named_values_and_dropped_maximum_snapshot(self):
        b=BattleState(profile(rebirth_count=1),level_for(2,2,3));a=list(b.aircraft.values())[1]
        self.assertLess(a.approach_duration,34);self.assertGreater(a.turn_rate,34);b.damage_aircraft(a.id,a.hp)
        self.assertEqual(len(b.enemies),6);self.assertTrue(all(e.max_hp==4 for e in b.enemies.values()))
