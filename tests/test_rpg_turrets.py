import unittest
from air_defense.entities import Enemy, V3, Turret
from air_defense.state import BattleState
from air_defense.combat import turret_damage
from air_defense.progression import new_profile, level_for

class RpgTurretTests(unittest.TestCase):
    def test_rpg_radius_airborne_no_aircraft_damage(self):
        p=new_profile(); p['upgrade_levels']['rpg']=1; p['unlocked_weapons'].append('RPG')
        b=BattleState(p,level_for(1,1,2)); b.player.weapon_slot=4
        center=b.player.eye+V3(0,0,8)
        for key,delta in (('a',0),('b',6),('c',6.01)):
            b.enemies[key]=Enemy(key,'GROUND_BOSS',center+V3(delta,-.9,0))
        b.aircraft['air-0'].position=center
        self.assertEqual(b.fire('a',ray_distance=8),'applied')
        self.assertEqual([b.enemies[k].hp for k in ('a','b','c')],[0,0,10])
        self.assertEqual(b.aircraft['air-0'].hp,1); self.assertEqual(b.player.rpg_ammo,2)

    def test_turret_three_dimensional_boundary_and_boss_floor(self):
        turret=Turret('t',V3(0,0,100)); boss=Enemy('e','GROUND_BOSS',V3(0,.1,132),phase='ground')
        self.assertTrue(turret.legal(boss))
        boss.position=V3(0,.1,132.01); self.assertFalse(turret.legal(boss))
        for _ in range(10): boss.hp-=turret_damage(boss)
        self.assertEqual(boss.hp,5)
        boss.hp=3; self.assertEqual(turret_damage(boss),0)

    def test_six_turrets_share_boss_floor(self):
        p=new_profile(); p['upgrade_levels'].update(auto_defense=1,auto_defense_capacity=5)
        b=BattleState(p,level_for(1,1,2))
        self.assertEqual(len(b.turrets),6)
        boss=Enemy('boss','GROUND_BOSS',V3(-8,0,55),phase='ground')
        b.enemies[boss.id]=boss
        for _ in range(300): b.step(1/120,__import__('air_defense.state',fromlist=['InputFrame']).InputFrame())
        self.assertGreaterEqual(boss.hp,5)
