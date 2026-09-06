import unittest
from air_defense.entities import Enemy, V3
from tests.fixtures import battle


class WeaponValidationTests(unittest.TestCase):
    def test_T11_invalid_attacks_preserve_resources(self):
        b = battle()
        b.select_weapon(3)
        before = (b.player.hp, dict(b.player.cooldowns), b.player.rpg_ammo)
        self.assertEqual(b.fire('air-0'), 'target_type')
        self.assertEqual(before, (b.player.hp, b.player.cooldowns, b.player.rpg_ammo))
        e = Enemy('e', 'NORMAL', V3(100, 0, 100), phase='ground')
        b.enemies[e.id] = e
        self.assertEqual(b.fire(e.id), 'range')
        self.assertEqual(e.hp, 3)

    def test_T12_ray_range_boundaries(self):
        for distance, expected in ((12, 'applied'), (12.01, 'range')):
            b = battle()
            b.select_weapon(3)
            e = Enemy('e', 'NORMAL', V3(-18, 0, 80), phase='ground')
            b.enemies[e.id] = e
            self.assertEqual(b.fire(e.id, ray_distance=distance), expected)
            self.assertEqual(e.hp, 2 if expected == 'applied' else 3)

    def test_blocked_attack_does_not_start_cooldown(self):
        b = battle()
        b.enemies['e'] = Enemy('e', 'NORMAL', V3(-18,0,75), phase='ground')
        b.select_weapon(3)
        self.assertEqual(b.fire('e', visible=False), 'blocked')
        self.assertEqual(b.player.cooldowns[3], 0)
