import unittest
from air_defense.progression import roster_for, level_for, campaign, new_profile, transact, caps


class ProgressionTests(unittest.TestCase):
    def test_T01_campaign_counts_and_invalid(self):
        for A, count in [(2,7),(3,12),(4,18),(5,25),(19,228)]:
            levels = list(campaign(A))
            self.assertEqual(len(levels), count)
            self.assertTrue(all('ARMORED_BOSS' not in x.roster for x in levels if x.a < A))
        for args in [(1,1,1),(0,1,2),(1,3,2),(3,1,2),(2,6,2),(True,1,2)]:
            with self.assertRaises(ValueError): roster_for(*args)

    def test_T02_formation_order(self):
        N,S,B='NORMAL','MANPOWER_SUPPORT','ARMORED_BOSS'
        for args, expected in [((2,2,2),(N,S)),((2,4,2),(B,S)),((2,5,2),(B,B)),((3,5,3),(B,S,S)),((3,7,3),(B,B,B))]:
            self.assertEqual(roster_for(*args), expected)

    def test_reward_replay(self):
        from tests.fixtures.expansion import request,operation_id
        p=new_profile();req=request(p,'reward',a=1,b=1,A=2)
        self.assertEqual(transact(p,operation_id(),req)['result_code'],'applied')
        self.assertTrue(transact(p,operation_id(),req)['replayed']);self.assertEqual(p['coins'],125)
