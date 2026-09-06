import unittest
from dataclasses import replace
from unittest.mock import patch
from air_defense.entities import Enemy,V3
from air_defense.deployment import WorldDefinition
from air_defense.projectiles import Rocket,CollisionHit,raycast_hit,explosion_targets

class RocketCollisionTests(unittest.TestCase):
    def test_thin_wall_swept_first_world_tie_and_normal(self):
        world=WorldDefinition(boxes=((V3(0,2,10),V3(10,4,.02)),))
        e=Enemy('e','NORMAL',V3(0,1.1,10.29))
        hit=raycast_hit(V3(0,2,0),V3(0,0,1),60,[e],world)
        self.assertEqual(hit.kind,'world');self.assertAlmostEqual(hit.distance,9.99);self.assertEqual(hit.normal,V3(0,0,-1))
        rocket=Rocket('r','W19',V3(0,2,0),V3(0,0,1),45,60,3,35,6)
        with patch('air_defense.projectiles.WORLD',world):
            with patch('air_defense.projectiles.raycast_hit',side_effect=lambda *args:raycast_hit(*args,world=world)):
                hit,status=rocket.update(1,[e])
        self.assertEqual(status,'hit');self.assertAlmostEqual(rocket.position.z,9.99)
    def test_range_and_lifetime_clip_without_explosion(self):
        for distance,life,z in ((2,3,2),(60,.01,.45)):
            r=Rocket('r','W19',V3(40,10,100),V3(0,0,1),45,distance,life,35,6)
            hit,status=r.update(.5,[]);self.assertIsNone(hit);self.assertEqual(status,'expired');self.assertAlmostEqual(r.position.z,100+z)
    def test_surface_offset_radius_endpoint_and_occlusion(self):
        world=WorldDefinition(boxes=((V3(0,2,10),V3(10,4,.2)),))
        hit=CollisionHit(0,V3(0,2,9.9),V3(0,0,-1),'world')
        enemies=[Enemy('near','NORMAL',V3(0,1.1,3.9)),Enemy('far','NORMAL',V3(0,1.1,3.89)),Enemy('behind','NORMAL',V3(0,1.1,11))]
        from air_defense.deployment import visible
        with patch('air_defense.projectiles.visible',side_effect=lambda a,b:visible(a,b,world)):
            self.assertEqual([e.id for e in explosion_targets(hit,6,enemies)],['near'])
