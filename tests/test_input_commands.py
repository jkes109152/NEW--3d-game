import unittest
from tests.fixtures.expansion import equipped
from air_defense.state import InputFrame
from air_defense.weapons import InputCommand


class CommandTests(unittest.TestCase):
    def test_short_edges_survive_no_fixed_step(self):
        b=equipped();b.advance(.001,InputFrame(commands=(InputCommand(1,'fire_down'),InputCommand(2,'fire_up'))))
        self.assertEqual(b.shot_number,0)
        b.advance(.008);self.assertEqual(b.shot_number,1);self.assertFalse(b.held)

    def test_sequence_order_and_duplicate_down(self):
        b=equipped();b.advance(1/120,InputFrame(commands=(InputCommand(1,'fire_down'),InputCommand(2,'select_slot',1))))
        self.assertEqual(b.runtime['W03'].magazine_rounds,11)
        b=equipped();b.advance(1/120,InputFrame(commands=(InputCommand(1,'select_slot',1),InputCommand(2,'fire_down'))))
        self.assertEqual(b.runtime['W03'].magazine_rounds,12)
        b=equipped();b.advance(1/120,InputFrame(commands=tuple(InputCommand(i,'fire_down') for i in range(4))))
        self.assertEqual(b.shot_number,1)

    def test_pause_priority_freeze_and_release_guard(self):
        b=equipped('W12');b.advance(1/120,InputFrame(commands=(InputCommand(1,'fire_down'),InputCommand(2,'pause'))))
        self.assertEqual(b.shot_number,0);before=b.elapsed
        b.advance(5);self.assertEqual(b.elapsed,before);b.resume()
        b.advance(1/120,InputFrame(commands=(InputCommand(3,'fire_down'),)))
        self.assertEqual(b.shot_number,0)
        b.advance(1/120,InputFrame(commands=(InputCommand(4,'fire_up'),InputCommand(5,'fire_down'))))
        self.assertEqual(b.shot_number,1)
