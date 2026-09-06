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

    def test_T03_reward_and_duplicate(self):
        for args, reward in [((1,1,2,0),125),((2,5,2,0),490),((3,7,3,1),1027)]:
            self.assertEqual(level_for(*args).reward,reward)
        p=new_profile()
        req={'kind':'reward','a':1,'b':1,'A':2}
        self.assertEqual(transact(p,'r1',req),'applied')
        transact(p,'r1',req)
        self.assertEqual(p['coins'],125)

    def test_T16_shop_and_T17_rebirth(self):
        p=new_profile(); p['coins']=3000
        for op in ('first','second'): self.assertEqual(transact(p,op,{'kind':'purchase','upgrade_id':'max_hp'}),'applied')
        self.assertEqual(p['coins'],2250)
        self.assertEqual(transact(p,'cap',{'kind':'purchase','upgrade_id':'auto_defense_capacity'}),'prerequisite_missing')
        p['coins']=1560; p['rebirth_available']=True
        self.assertEqual(transact(p,'rb',{'kind':'rebirth'}),'applied')
        self.assertEqual((p['coins'],p['rebirth_count'],p['max_aircraft_count']),(0,1,3))
        self.assertEqual(p['upgrade_levels']['max_hp'],2)
        self.assertEqual(caps(1)['max_hp'],6)

    def test_conflict_does_not_mutate(self):
        p=new_profile(); p['coins']=1000
        transact(p,'same',{'kind':'purchase','upgrade_id':'max_hp'})
        self.assertEqual(transact(p,'same',{'kind':'purchase','upgrade_id':'armor'}),'operation_conflict')
        self.assertEqual(p['coins'],750)
