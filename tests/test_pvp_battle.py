import unittest
from unittest.mock import patch
from air_defense.pvp import PvpBattle
from air_defense.entities import angles, V3

ROSTER = [dict(id='g', name='地面', team='ground'), dict(id='a', name='空中', team='air')]


class PvpBattleTests(unittest.TestCase):
    def setUp(self):
        self.b = PvpBattle('test', ROSTER, 180)
        self.b.actors['g']['position'] = [0, 0, 0]
        self.b.actors['a']['position'] = [0, 10, 50]
        yaw, pitch = angles(V3(0, 8.4, 50))
        self.b.actors['g'].update(yaw=yaw, pitch=pitch)
        self.frame = dict(suspended=False, stream='g', inputSeq=1, commands=[dict(sequence=1, kind='toggle_aim')])

    def tick(self, seconds):
        with patch('air_defense.pvp.move_actor'):
            for _ in range(round(seconds * 120)):
                self.b.advance(1 / 120, {'g': self.frame})

    def test_lock_loss_and_cooldown(self):
        self.tick(2.95)
        self.assertFalse(self.b.locks['g'].ready())
        self.tick(.05)
        self.assertTrue(self.b.locks['g'].ready())
        self.b.actors['a']['position'] = [60, 10, 50]
        self.tick(.375)
        self.assertAlmostEqual(self.b.locks['g'].progress['a'], .5, places=6)
        self.assertFalse(self.b.locks['g'].valid)
        self.tick(.375)
        self.assertAlmostEqual(self.b.locks['g'].progress['a'], 0)

    def test_two_hits_and_repeated_fire(self):
        self.tick(3)
        self.frame['commands'] += [dict(sequence=2, kind='fire_down')]
        self.tick(.6)
        self.assertEqual(self.b.actors['a']['hp'], 1)
        self.assertAlmostEqual(self.b.actors['g']['next_fire'], 4.25, delta=.02)
        self.tick(3)
        self.assertEqual(self.b.actors['a']['hp'], 0)
        self.assertEqual(self.b.result['winner'], 'ground')
        self.assertEqual(self.b.actors['g']['kills'], 1)
        self.assertEqual(self.b.missile_sequence, 2)

    def test_projection_matches_vertical_fov_and_obstacles(self):
        self.b.actors['a']['position'] = [0, 8, 50]
        self.b.actors['g'].update(yaw=0, pitch=0)
        self.tick(3)
        self.assertTrue(self.b.locks['g'].ready())
        self.b.actors['a']['position'] = [0, 9, 50]
        self.tick(.01)
        self.assertFalse(self.b.locks['g'].valid)

    def test_ground_base_movement(self):
        b = PvpBattle('motion', ROSTER, 180)
        start = b.actors['g']['position'][:]
        b.advance(1, {'g': dict(suspended=False, move_z=1)})
        self.assertAlmostEqual(b.actors['g']['position'][2] - start[2], 6)


if __name__ == '__main__': unittest.main()
