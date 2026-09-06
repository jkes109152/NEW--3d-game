import unittest
from air_defense.state import BattleState, InputFrame
from air_defense.entities import Enemy, V3
from air_defense.progression import new_profile, level_for

class MixedBattleTests(unittest.TestCase):
    def test_two_aircraft_continue_while_crew_descends(self):
        b=BattleState(new_profile(),level_for(2,3,2))
        b.damage_aircraft(list(b.aircraft)[0],b.aircraft[list(b.aircraft)[0]].hp); before=b.aircraft[list(b.aircraft)[1]].position
        for _ in range(60): b.advance(1/60,InputFrame())
        self.assertNotEqual(b.aircraft[list(b.aircraft)[1]].position,before)
        self.assertEqual(len(b.enemies),6)
        self.assertTrue(all(e.phase=='descending' for e in b.enemies.values()))
        self.assertEqual(b.phase,'active')

    def test_three_immediate_failure_reasons(self):
        for reason in ('player','city','impact'):
            with self.subTest(reason=reason):
                b=BattleState(new_profile(),level_for(1,1,2))
                if reason=='player':
                    b.player.hp=1
                    b.enemies['e']=Enemy('e','NORMAL',b.player.position+V3(0,0,4),phase='ground')
                elif reason=='city':
                    b.city.hp=.01
                    b.enemies['e']=Enemy('e','NORMAL',V3(0,0,-45),phase='ground')
                else:
                    a=b.aircraft[list(b.aircraft)[0]]; a.position=V3(0,10,-51); a.elapsed=a.duration
                b.advance(1/120,InputFrame())
                self.assertEqual((b.phase,b.failure_reason),('failure',reason))
