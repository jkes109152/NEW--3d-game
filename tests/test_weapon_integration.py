import unittest
from tests.fixtures import battle
from air_defense.entities import Enemy, V3
from air_defense.state import InputFrame

class WeaponIntegrationTests(unittest.TestCase):
    def test_ground_weapon_damage_event_once_and_last_enemy_settles(self):
        b=battle(); b.player.weapon_slot=3
        for a in b.aircraft.values(): a.hp=0; a.status='destroyed'
        e=Enemy('e','NORMAL',b.player.eye+V3(0,-.9,8),phase='ground',hp=1); b.enemies[e.id]=e
        self.assertEqual(b.fire('e',ray_distance=8),'applied')
        self.assertEqual(b.phase,'success')
        self.assertEqual(sum(x['kind']=='hit' for x in b.events),1)
        self.assertFalse(b.damage_enemy('e',1,'visual-effect'))

    def test_weapon_switch_preserves_resources_clears_aim(self):
        b=battle(); b.player.aiming=True; b.player.cooldowns[1]=1; b.player.rpg_ammo=1
        b.lock.progress={'air-0':1}
        b.select_weapon(2); b.select_weapon(1)
        self.assertFalse(b.player.aiming); self.assertEqual(b.lock.progress,{})
        self.assertEqual(b.player.cooldowns[1],1); self.assertEqual(b.player.rpg_ammo,1)
