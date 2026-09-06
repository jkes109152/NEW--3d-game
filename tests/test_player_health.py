import unittest
from air_defense.entities import Player

class PlayerHealthTests(unittest.TestCase):
    def test_armor_minimum_zero_damage_and_regen_crossing_five(self):
        p=Player(hp=50,armor=20)
        self.assertEqual(p.hurt(8),1)
        p.tick(4.9); p.hurt(0); p.tick(.2)
        self.assertAlmostEqual(p.hp,49.2)
        p.tick(20); self.assertEqual(p.healed,20); self.assertEqual(p.hp,69)
        p.hurt(2); p.tick(20); self.assertEqual(p.hp,68)

    def test_dead_player_does_not_heal(self):
        p=Player(hp=0); p.tick(30)
        self.assertEqual(p.hp,0)
