import unittest
from copy import deepcopy
from unittest.mock import patch
from air_defense.pvp import PvpBattle
from air_defense.pvp_motion import STEP


class PvpLifecycleTests(unittest.TestCase):
    def battle(self):
        b=PvpBattle('life',[dict(id='g',name='地面',team='ground'),dict(id='a',name='空中',team='air')],180)
        b.actors['a']['position']=[0,40,50]
        return b

    def test_time_and_deadline_hit(self):
        b=self.battle();b.elapsed=180-STEP;b.tick=21599
        b.actors['a']['hp']=1
        b.missiles['1']=dict(id='1',owner_id='g',target_id='a',position=[0,40,50],forward=[0,0,1],age=0)
        b.advance(STEP,{})
        self.assertEqual(b.result['winner'],'ground')
        state=deepcopy(b.result);b.advance(1,{})
        self.assertEqual(b.result,state)

    def test_before_time_and_timeout(self):
        b=self.battle()
        b.advance(STEP,{})
        self.assertIsNone(b.result)
        b.elapsed=180-STEP;b.tick=21599;b.advance(STEP,{})
        self.assertEqual(b.result['winner'],'air');self.assertEqual(b.result['reason'],'timeout')

    def test_departures_and_abort_precedence(self):
        for departed,winner,reason in [(['a'],'ground','air_eliminated'),(['g'],'air','ground_departed'),(['g','a'],None,'all_departed')]:
            b=self.battle();b.advance(STEP,{},departed)
            self.assertEqual((b.result['winner'],b.result['reason']),(winner,reason))
            self.assertTrue(all(a['kills']==0 for a in b.actors.values()))

    def test_gap_rejected_without_time_loss(self):
        b=self.battle()
        for dt in [1.001,-1,float('nan'),float('inf')]:
            with self.assertRaises(ValueError):b.advance(dt,{})
        self.assertEqual(b.elapsed,0)
        with patch('air_defense.pvp.move_actor'):
            b.advance(1,{})
        self.assertEqual(b.tick,120);self.assertAlmostEqual(b.elapsed,1)

    def test_expired_and_cancelled_look_never_replayed(self):
        b=self.battle()
        b.advance(STEP,{'g':dict(suspended=False,stream='s',inputSeq=1,look_total=[10,0],commands=[dict(sequence=1,kind='toggle_aim'),dict(sequence=2,kind='fire_down')])})
        b.advance(STEP,{'g':dict(suspended=True,stream='s',inputSeq=2,look_total=[30,0],cancelThrough=2)})
        b.advance(STEP,{'g':dict(suspended=False,stream='s',inputSeq=3,look_total=[30,0],commands=[dict(sequence=2,kind='fire_down')])})
        self.assertEqual(b.actors['g']['yaw'],10)
        self.assertFalse(b.actors['g']['firing'])
        self.assertEqual(b.actors['g']['inputAck']['look_total'],[30,0])


if __name__=='__main__':unittest.main()
