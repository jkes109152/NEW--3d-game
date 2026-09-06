import unittest
from air_defense.entities import Player, Enemy, V3, visible_between, ray_box

class WorldCollisionTests(unittest.TestCase):
    def test_player_cannot_cross_cover_or_boundary(self):
        p=Player(position=V3(-29,0,70))
        for _ in range(500): p.move(0,1,False,1/120)
        self.assertLessEqual(p.position.z,74.06)
        p.position=V3(59.5,0,100)
        for _ in range(20): p.move(1,0,False,1/120)
        self.assertLessEqual(p.position.x,59.55)

    def test_cover_blocks_ray_and_person_envelope(self):
        self.assertFalse(visible_between(V3(-29,1,70),V3(-29,1,80)))
        self.assertTrue(visible_between(V3(0,1,70),V3(0,1,80)))
        e=Enemy('e','NORMAL',V3(0,0,10),phase='ground')
        self.assertEqual(e.hit_envelope,(e.center,V3(.8,1.8,.6)))
        self.assertAlmostEqual(ray_box(V3(0,.9,0),V3(0,0,1),*e.hit_envelope),9.7)
