import sys
import unittest
from air_defense.state import InputFrame, BattleState
from tests.fixtures import battle


class ContractTests(unittest.TestCase):
    def test_rule_import_has_no_engine(self):
        self.assertNotIn('ursina', sys.modules)

    def test_immutable_input_and_safe_illegal_slot(self):
        frame = InputFrame()
        with self.assertRaises(AttributeError): frame.move_x = 1
        b = battle()
        before = b.player.weapon_slot
        self.assertEqual(b.select_weapon(4), 'weapon_locked')
        self.assertEqual(b.player.weapon_slot, before)

    def test_summary_does_not_expose_mutable_state(self):
        b = battle()
        snapshot = b.snapshot()
        snapshot['player']['hp'] = -10
        self.assertEqual(b.player.hp, 100)
