"""PvP 固定世界與共用移動的公開契約。"""
import unittest
from air_defense.pvp_motion import STEP, BOXES, spawn_actor, visible, crash_fraction
from air_defense.entities import V3


class PvpMotionTests(unittest.TestCase):
    def test_safe_separate_spawns(self):
        self.assertEqual(STEP, 1 / 120)
        points = set()
        for team in ('ground', 'air'):
            for index in range(4):
                actor = spawn_actor(str(index), team, index)
                point = tuple(actor['position'])
                self.assertNotIn(point, points)
                points.add(point)
                self.assertIsNone(crash_fraction(V3(*point), V3(*point)) if team == 'air' else None)
                self.assertEqual(actor['hp'], 2 if team == 'air' else 1)
                self.assertEqual(actor['speed'], 40 if team == 'air' else 6)
        self.assertEqual(len(BOXES), 4)

    def test_sweep_and_visibility(self):
        self.assertIsNotNone(crash_fraction(V3(-60, 6, -25), V3(-30, 6, -25)))
        self.assertFalse(visible(V3(-60, 6, -25), V3(-30, 6, -25)))
        self.assertTrue(visible(V3(0, 2, 0), V3(0, 40, 70)))
        self.assertIsNotNone(crash_fraction(V3(0, 3, 0), V3(0, 0, 0)))

    def test_bad_team_and_spawn_rejected(self):
        with self.assertRaises(ValueError):
            spawn_actor('x', 'other', 0)
        with self.assertRaises(ValueError):
            spawn_actor('x', 'air', 4)


if __name__ == '__main__':
    unittest.main()
