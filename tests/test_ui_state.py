import unittest
from unittest.mock import Mock
from air_defense.ui import shop_key, reticle_kind, GameUI
from air_defense.progression import UPGRADES
from air_defense.main import GameController
from air_defense.state import AppState
from tests.fixtures import battle

class UIStateTests(unittest.TestCase):
    def test_shop_shortcuts_match_definition_ids(self):
        self.assertEqual([shop_key(k) for k in '1234567890'],[row[0] for row in UPGRADES])
        self.assertIsNone(shop_key('enter'))
        for slot in range(1,6):
            self.assertEqual(reticle_kind(slot,False),'crosshair')
            self.assertEqual(reticle_kind(slot,True),'lock' if slot in (1,5) else 'scope' if slot==2 else 'crosshair')

    def test_escape_priority_e_g_no_effect_and_toggle_aim(self):
        c=object.__new__(GameController); c.record_input=False; c.state=AppState(); c.state.battle=battle()
        c.state.screen='battle'; c.ui=Mock(); c.back=Mock()
        before=c.state.battle.snapshot()
        c.input('e'); c.input('g'); self.assertEqual(c.state.battle.snapshot(),before)
        c.input('escape'); c.back.assert_called_once(); c.ui.input.assert_not_called()
        c.input('right mouse down'); self.assertTrue(c.state.battle.player.aiming)
        c.input('right mouse down'); self.assertFalse(c.state.battle.player.aiming)

    def test_toast_reuses_single_label(self):
        ui=object.__new__(GameUI); ui.toast_label=Mock(); ui.toast_back=Mock()
        label=ui.toast_label
        ui.toast('冷卻中'); ui.toast('冷卻中'); ui.tick(3)
        self.assertIs(ui.toast_label,label); self.assertEqual(label.text,'')
