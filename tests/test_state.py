"""固定時間、暫停與清理的公開契約。"""
import unittest
from air_defense.state import BattleState, InputFrame, SimulationClock
from air_defense.progression import new_profile, level_for


class StateTests(unittest.TestCase):
    def test_T22_pause_does_not_catch_up(self):
        b = BattleState(new_profile(), level_for(1, 1, 2), seed=1)
        b.advance(.05)
        before = b.snapshot()
        b.pause()
        for _ in range(10): b.advance(20)
        self.assertEqual(b.elapsed, before['elapsed'])
        self.assertEqual(b.aircraft[list(b.aircraft)[0]].position.tuple(), before['aircraft'][0]['position'])
        b.resume()
        b.advance(0)
        self.assertEqual(b.elapsed, before['elapsed'])

    def test_T21_teardown_and_old_attempt(self):
        b = BattleState(new_profile(), level_for(1, 1, 2), seed=1)
        b.teardown()
        self.assertEqual(sum(b.metrics().values()), 0)
        self.assertFalse(b.accept_event({'attempt_id':'old', 'kind':'damage'}))

    def test_clock_clamps_hitches(self):
        c = SimulationClock()
        self.assertEqual(c.steps(10), 8)
        self.assertGreater(c.dropped_steps, 0)
        self.assertEqual(c.steps(0), 0)

    def test_deterministic_input_replay(self):
        args = (new_profile(), level_for(2, 2, 2))
        a, b = (BattleState(*args, seed=10, attempt_id='same') for _ in range(2))
        for _ in range(120):
            a.advance(1/60, InputFrame(move_z=1))
            b.advance(1/60, InputFrame(move_z=1))
        self.assertEqual(a.snapshot(), b.snapshot())
