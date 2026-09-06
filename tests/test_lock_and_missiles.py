import unittest
from air_defense.combat import LockState
from air_defense.entities import Missile, Aircraft, V3


class LockMissileTests(unittest.TestCase):
    def test_T08_aim_assist_only_purchased_and_aimed_with_three_degree_limit(self):
        from air_defense.combat import aim_assist
        from air_defense.entities import Aircraft, Player, V3
        from air_defense.progression import new_profile
        p=new_profile(); player=Player(); target=Aircraft('t','NORMAL',player.eye+V3(20,10,80))
        player.aiming=True
        self.assertEqual(aim_assist(p,player,target,1),(0,0))
        p['upgrade_levels']['aa_aim_assist']=1
        yaw,pitch=aim_assist(p,player,target,.1)
        self.assertLessEqual((yaw*yaw+pitch*pitch)**.5,.3+1e-9)
        player.aiming=False; self.assertEqual(aim_assist(p,player,target,1),(0,0))

    def test_missile_turn_rate_is_bounded(self):
        from math import acos, degrees
        from air_defense.entities import Aircraft, Missile, V3
        target=Aircraft('t','NORMAL',V3(100,0,0)); m=Missile('m','t',V3(),V3(0,0,1))
        m.update(.01,target)
        self.assertLessEqual(degrees(acos(m.forward.dot(V3(0,0,1)))),2.4+1e-7)

    def test_T07_acquire_decay_return_switch(self):
        lock = LockState()
        lock.update(3, ['a'], {'a','b'}, True, False, 3)
        self.assertEqual(lock.progress['a'], 1)
        lock.update(.375, [], {'a','b'}, True, False, 3)
        self.assertAlmostEqual(lock.progress['a'], .5)
        self.assertFalse(lock.ready())
        lock.update(.375, [], {'a','b'}, True, False, 3)
        self.assertEqual(lock.progress.get('a',0), 0)
        lock.update(1, ['b'], {'a','b'}, True, False, 3)
        self.assertNotIn('a', lock.progress)
        self.assertAlmostEqual(lock.progress['b'], 1/3)

    def test_T10_swept_hit_wins_expiry_and_target_is_fixed(self):
        target = Aircraft('a','NORMAL',V3(0,0,5))
        missile = Missile('m','a',V3(0,0,0),V3(0,0,1), age=4.99)
        self.assertEqual(missile.update(.1, target), 'hit')
        self.assertEqual(missile.target_id, 'a')
        missing = Missile('m2','gone',V3(0,0,0),V3(0,0,1))
        self.assertEqual(missing.update(.1,None),'expired')
