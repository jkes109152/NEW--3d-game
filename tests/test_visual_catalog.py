import unittest
from air_defense.visual_catalog import RECIPES,ARMOR_PARTS,PALETTE
from air_defense.catalog import WEAPONS

class VisualCatalogTests(unittest.TestCase):
    def test_twenty_distinct_two_part_silhouettes_and_six_armor_recipes(self):
        self.assertEqual(set(RECIPES),set(WEAPONS));self.assertEqual(len(ARMOR_PARTS),6)
        signatures=set()
        for key,parts in RECIPES.items():
            self.assertGreaterEqual(len(parts),2);self.assertGreaterEqual(len({p[1:3] for p in parts}),2)
            signatures.add(tuple(parts));self.assertTrue(all(len(p)==4 and all(v>0 for v in p[2]) for p in parts))
        self.assertEqual(len(signatures),20);self.assertEqual(len(PALETTE),5)
