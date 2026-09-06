import unittest
from air_defense.progression import campaign, level_for, next_level, roster_for

class CampaignProgressionTests(unittest.TestCase):
    def test_counts_and_contiguous_cursor_for_large_campaign(self):
        for A,total in ((2,7),(3,12),(4,18),(5,25),(19,228)):
            levels=list(campaign(A)); self.assertEqual(len(levels),total)
            for before,after in zip(levels,levels[1:]):
                self.assertEqual(next_level(before),(after.a,after.b))
                self.assertEqual(len(before.roster),before.a)
            self.assertTrue(levels[-1].is_final); self.assertEqual(next_level(levels[-1]),(1,1))
            self.assertNotIn('FAST',set(kind for level in levels for kind in level.roster))

    def test_invalid_values_including_boolean_and_empty_campaign(self):
        for values in ((0,1,2),(1,3,2),(2,6,2),(3,1,2),(1,1,True),(1,1,1.0)):
            with self.assertRaises(ValueError): roster_for(*values)
        for A in (0,1,-1,True):
            with self.assertRaises(ValueError): list(campaign(A))
