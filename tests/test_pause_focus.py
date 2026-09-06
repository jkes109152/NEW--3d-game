import unittest
from unittest.mock import Mock
from tests.fixtures import battle
from air_defense.main import GameController
from air_defense.state import InputFrame
from air_defense.entities import Enemy, V3, Missile

class PauseFocusTests(unittest.TestCase):
    def test_focus_loss_pauses_and_all_clocks_freeze(self):
        c=object.__new__(GameController); c.focus_checks=True; c.pause=Mock()
        window=Mock(); window.getProperties.return_value.getForeground.return_value=False
        c.window_event(window); c.pause.assert_called_once()
        b=battle(); b.enemies['e']=Enemy('e','NORMAL',V3(0,20,100))
        b.missiles['m']=Missile('m','air-0',b.player.eye,b.player.forward)
        b.player.cooldowns[1]=1; b.player.hp=50; b.player.since_damage=4
        b.lock.progress={'air-0':.5}; b.pause(); before=b.snapshot()
        b.advance(45,InputFrame(fire_pressed=True,jump_pressed=True))
        self.assertEqual(b.snapshot(),before)
        b.resume(); b.advance(0,InputFrame())
        self.assertEqual(b.elapsed,0); self.assertEqual(b.player.hp,50)
