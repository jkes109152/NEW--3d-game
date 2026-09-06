import unittest
from air_defense.entities import Enemy,V3
from tests.fixtures.expansion import equipped

class WeaponValidationTests(unittest.TestCase):
    def test_missed_ground_shot_consumes_ammo_and_cooldown(self):
        b=equipped();hp=next(iter(b.aircraft.values())).hp
        self.assertEqual(b.fire(),'applied');self.assertEqual(b.runtime['W03'].magazine_rounds,11)
        self.assertEqual(next(iter(b.aircraft.values())).hp,hp)
        self.assertEqual(b.fire(),'cooldown');self.assertEqual(b.runtime['W03'].magazine_rounds,11)
    def test_pistol_actual_envelope_range_boundary(self):
        for distance,hp in ((24,2),(24.01,3)):
            b=equipped();e=Enemy('e','NORMAL',b.player.position+V3(0,0,distance+.3),phase='ground');b.enemies[e.id]=e
            b.fire();self.assertEqual(e.hp,hp)
    def test_wall_blocks_damage_but_does_not_prevent_shooting(self):
        b=equipped();b.player.position=V3(-29,0,72)
        e=Enemy('e','NORMAL',V3(-29,0,80),phase='ground');b.enemies[e.id]=e
        self.assertEqual(b.fire(),'applied');self.assertEqual(e.hp,3);self.assertEqual(b.runtime['W03'].magazine_rounds,11)
