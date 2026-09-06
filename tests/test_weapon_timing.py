import unittest
from air_defense.state import InputFrame
from air_defense.weapons import InputCommand
from tests.fixtures.expansion import equipped


class TimingTests(unittest.TestCase):
    def test_auto_fractional_interval_across_render_rates(self):
        counts=[]
        for hz in (30,60,144):
            b=equipped('W12');shots=0
            for i in range(hz):
                b.advance(1/hz,InputFrame(commands=(InputCommand(1,'fire_down'),) if i==0 else ()))
                shots+=sum(e['kind']=='weapon_fire' for e in b.events)
            counts.append(shots)
        self.assertEqual(counts,[17,17,17])

    def test_semi_and_bolt_require_new_down(self):
        for wid in ('W03','W17'):
            b=equipped(wid)
            b.advance(1/120,InputFrame(commands=(InputCommand(1,'fire_down'),)))
            for _ in range(120):b.advance(1/120)
            self.assertEqual(b.shot_number,1)
            b.advance(1/120,InputFrame(commands=(InputCommand(2,'fire_up'),InputCommand(3,'fire_down'))))
            self.assertEqual(b.shot_number,2)

    def test_burst_release_completes_but_switch_cancels(self):
        b=equipped('W04')
        b.advance(1/120,InputFrame(commands=(InputCommand(1,'fire_down'),InputCommand(2,'fire_up'))))
        for _ in range(30):b.advance(1/120)
        self.assertEqual(b.shot_number,3)
        c=equipped('W04');c.runtime['W04'].magazine_rounds=2
        c.advance(1/120,InputFrame(commands=(InputCommand(1,'fire_down'),)))
        for _ in range(30):c.advance(1/120)
        self.assertEqual(c.shot_number,2)
        self.assertIsNotNone(c.runtime['W04'].reload_finish_at)
        d=equipped('W04');d.advance(1/120,InputFrame(commands=(InputCommand(1,'fire_down'),InputCommand(2,'select_slot',1))))
        for _ in range(30):d.advance(1/120)
        self.assertEqual(d.shot_number,1)

    def test_switch_cancels_reload_without_refill_and_preserves_cooldown(self):
        b=equipped('W03');b.fire();r=b.runtime['W03'];deadline=r.next_shot_at
        self.assertTrue(b.reload());b.select_weapon(1);b.select_weapon(2)
        self.assertEqual(r.magazine_rounds,11);self.assertIsNone(r.reload_finish_at)
        self.assertEqual(r.next_shot_at,deadline);self.assertEqual(b.fire(),'cooldown')

    def test_rocket_quota_per_weapon_and_per_level(self):
        for wid,quota in (('W19',3),('W20',5)):
            b=equipped(wid)
            for _ in range(quota):
                self.assertEqual(b.fire(),'applied')
                for _ in range(310):b.advance(1/120)
            self.assertEqual(b.runtime[wid].quota_remaining,0)
            self.assertEqual(b.fire(),'ammo');self.assertEqual(equipped(wid).runtime[wid].quota_remaining,quota)
