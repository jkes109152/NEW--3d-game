import unittest
from air_defense.entities import Enemy,V3,Turret
from air_defense.combat import turret_damage
from air_defense.state import BattleState
from air_defense.progression import level_for
from tests.fixtures.expansion import equipped,profile,operation_id

class RpgTurretTests(unittest.TestCase):
    def test_rpg_flight_then_damage_never_aircraft_or_friendlies(self):
        b=equipped('W19');b.player.position=V3(40,0,100)
        e=Enemy('e','GROUND_BOSS',V3(40,0,108),phase='ground');b.enemies[e.id]=e
        a=next(iter(b.aircraft.values()));a.position=V3(40,1.6,104)
        self.assertEqual(b.fire(),'applied');self.assertEqual(e.hp,10)
        for _ in range(25):b.step(1/120)
        self.assertEqual(e.hp,0);self.assertEqual(a.hp,1);self.assertEqual(b.city.hp,100);self.assertEqual(b.runtime['W19'].quota_remaining,2)
    def test_turret_horizontal_boundary_and_exact_odd_boss_floor(self):
        t=Turret('t',V3(40,0,100));e=Enemy('e','GROUND_BOSS',V3(40,0,132),phase='ground',effective_max_hp=11)
        self.assertTrue(t.legal(e));e.position=V3(40,0,132.01);self.assertFalse(t.legal(e))
        for _ in range(20):e.hp-=turret_damage(e)
        self.assertEqual(e.hp,5.5)
    def test_twelve_owned_towers_without_fixed_six_limit(self):
        p=profile(rebirth_count=6)
        p['owned_turrets']=[dict(instance_id='turret-'+operation_id(i),turret_id='T01') for i in range(12)]
        p['confirmed_loadout']['deployments']=[dict(instance_id=t['instance_id'],x=40,z=80+4*i) for i,t in enumerate(p['owned_turrets'])]
        b=BattleState(p,level_for(1,1,8));self.assertEqual(len(b.turrets),12)
