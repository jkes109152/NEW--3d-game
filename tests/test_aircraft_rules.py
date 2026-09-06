import unittest
from math import degrees, acos
from air_defense.entities import Aircraft, V3, direction
from air_defense.config import AIRCRAFT

class AircraftTests(unittest.TestCase):
    def test_four_types_steering_warning_and_swept_impact(self):
        for kind,(hp,duration,amp,freq,yaw_rate,pitch_rate,_) in AIRCRAFT.items():
            with self.subTest(kind=kind):
                a=Aircraft('a',kind,V3(0,32,210))
                self.assertEqual(a.hp,hp); warned=False
                for _ in range(int((duration+4)*120)):
                    yaw,pitch=a.yaw,a.pitch
                    a.update(1/120)
                    self.assertLessEqual(abs((a.yaw-yaw+180)%360-180),yaw_rate/120+1e-7)
                    self.assertLessEqual(abs(a.pitch-pitch),pitch_rate/120+1e-7)
                    warned |= a.remaining<=8
                    if a.status=='impact': break
                self.assertTrue(warned); self.assertEqual(a.status,'impact')
