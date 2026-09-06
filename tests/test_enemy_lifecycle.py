import unittest
from air_defense.entities import V3
from tests.fixtures import battle


class EnemyLifecycleTests(unittest.TestCase):
    def test_T06_unique_drop_and_airborne_damage(self):
        b = battle()
        b.aircraft['air-0'].kind = 'MANPOWER_SUPPORT'
        b.aircraft['air-0'].position = V3(-18,20,100)
        b.damage_aircraft('air-0',1)
        b.damage_aircraft('air-0',1)
        self.assertEqual(len(b.enemies),6)
        for _ in range(450): b.step(1/120)
        self.assertTrue(all(e.phase=='descending' for e in b.enemies.values()))
        for _ in range(30): b.step(1/120)
        self.assertTrue(all(e.phase=='ground' for e in b.enemies.values()))

    def test_zero_drop_can_complete(self):
        b = battle()
        b.aircraft['air-0'].kind='FAST'
        b.damage_aircraft('air-0',1)
        b.check_outcome()
        self.assertEqual(b.phase,'success')
