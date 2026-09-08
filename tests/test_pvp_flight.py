import unittest
from copy import deepcopy
from air_defense.pvp import PvpBattle, predict
from air_defense.pvp_motion import spawn_actor, move_actor, STEP


class PvpFlightTests(unittest.TestCase):
    def test_speed_turn_and_roll_limits(self):
        a=spawn_actor('a','air',0)
        for _ in range(120): move_actor(a,dict(suspended=False,throttle=1,turn_x=1,turn_y=1,roll=1),STEP)
        self.assertAlmostEqual(a['speed'],52)
        self.assertAlmostEqual(a['yaw'],300)
        self.assertEqual(a['pitch'],70)
        self.assertAlmostEqual(a['roll'],180)
        for _ in range(1200): move_actor(a,dict(suspended=False,throttle=-1),STEP)
        self.assertEqual(a['speed'],24)

    def test_suspension_continues_heading_and_speed(self):
        a=spawn_actor('a','air',0)
        before=deepcopy(a)
        for _ in range(120):move_actor(a,dict(suspended=True,throttle=-1,turn_x=1),STEP)
        self.assertAlmostEqual(a['position'][2],before['position'][2]-40)
        self.assertEqual(a['speed'],40);self.assertEqual(a['yaw'],180)

    def battle(self):
        return PvpBattle('flight',[dict(id='g',name='地面',team='ground'),dict(id='a',name='空中',team='air')],180)

    def test_collision_and_no_respawn(self):
        b=self.battle();b.actors['a'].update(position=[0,2,0],pitch=70)
        b.advance(.1,{})
        self.assertFalse(b.actors['a']['alive']);self.assertEqual(b.actors['a']['eliminationReason'],'crash')
        b.advance(1,{'a':dict(suspended=False,stream='new')})
        self.assertFalse(b.actors['a']['alive'])

    def test_boundary_return_and_deadline(self):
        b=self.battle();a=b.actors['a'];a.update(position=[101,40,0],yaw=0,outside=4.98)
        b.advance(STEP,{});self.assertTrue(a['alive'])
        a['position'][0]=100;b.advance(STEP,{})
        self.assertEqual(a['outside'],0)
        a.update(position=[101,40,0],outside=5-STEP)
        b.advance(STEP,{})
        self.assertFalse(a['alive']);self.assertEqual(a['eliminationReason'],'boundary')

    def test_prediction_only_moves_and_does_not_damage(self):
        a=spawn_actor('a','air',0)
        frames=[dict(stream='s',inputSeqAtCapture=i, input=dict(suspended=False,throttle=1)) for i in range(120)]
        moved=predict(a,frames)
        self.assertEqual(a['position'][2],70)
        self.assertLess(moved['position'][2],30)
        self.assertTrue(moved['alive']);self.assertEqual(moved['hp'],2)


if __name__=='__main__':unittest.main()
