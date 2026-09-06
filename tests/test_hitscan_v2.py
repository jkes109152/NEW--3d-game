import unittest
from air_defense.entities import Enemy,V3
from tests.fixtures.expansion import equipped

class HitscanTests(unittest.TestCase):
    def test_sniper_over_180_uses_actual_range(self):
        for wid,hp in [('W17',10),('W18',5)]:
            b=equipped(wid);b.player.position=V3(40,0,-10);e=Enemy('e','GROUND_BOSS',V3(40,0,190),phase='ground');b.enemies[e.id]=e
            self.assertEqual(b.fire(),'applied');self.assertEqual(e.hp,hp)
    def test_eight_pellets_same_enemy_and_first_hit_only(self):
        b=equipped('W15');b.player.position=V3(40,0,100)
        a=Enemy('a','GROUND_BOSS',V3(40,0,102),phase='ground');z=Enemy('z','GROUND_BOSS',V3(40,0,104),phase='ground');b.enemies={a.id:a,z.id:z}
        b.fire();self.assertAlmostEqual(a.hp,6.8);self.assertEqual(z.hp,10)
        self.assertEqual(sum(e['kind']=='hit' for e in b.events),8);self.assertEqual(b.runtime['W15'].magazine_rounds,5)
