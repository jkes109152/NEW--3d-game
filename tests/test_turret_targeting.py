import unittest
from air_defense.entities import Enemy,Turret,V3,Aircraft
from tests.fixtures.expansion import equipped

class TurretTargetingTests(unittest.TestCase):
    def test_horizontal_endpoints_stable_tie_and_boss_half(self):
        b=equipped();b.turrets={'t':Turret('t',V3(40,0,100))}
        b.enemies={k:Enemy(k,'GROUND_BOSS',V3(40,0,132),phase='ground',effective_max_hp=11) for k in ('b','a')}
        b.tick_turrets(0);self.assertEqual(b.turrets['t'].target_id,'a');self.assertEqual(b.enemies['a'].hp,10)
        for i in range(10):b.elapsed+=.2;b.tick_turrets(.2)
        self.assertEqual(b.enemies['a'].hp,5.5);self.assertGreaterEqual(b.enemies['b'].hp,5.5)
        b.enemies={};self.assertFalse(b.turrets['t'].legal(Enemy('far','NORMAL',V3(40,0,132.01),phase='ground')))
    def test_aa_one_second_lock_reacquire_two_second_cooldown(self):
        b=equipped();b.turrets={'t':Turret('t',V3(40,0,100),turret_type_id='T03')};a=next(iter(b.aircraft.values()));a.position=V3(40,20,130)
        b.tick_turrets(0)
        b.elapsed=.99;b.tick_turrets(.99);self.assertEqual(len(b.missiles),0)
        b.elapsed=1;b.tick_turrets(.01);self.assertEqual(len(b.missiles),1)
        b.elapsed=2.99;b.tick_turrets(1.99);self.assertEqual(len(b.missiles),1)
        b.elapsed=3;b.tick_turrets(.01);self.assertEqual(len(b.missiles),2)
        b.elapsed=3.99;b.tick_turrets(.99);self.assertEqual(len(b.missiles),2)
        a.position=V3(40,20,281);b.tick_turrets(.1);self.assertIsNone(b.turrets['t'].target_id)
