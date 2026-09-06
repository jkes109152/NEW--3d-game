import unittest
from air_defense.catalog import WEAPONS, ARMORS, TURRETS, ATTACHMENTS, applicable_upgrade, upgrade_cap
class CatalogTests(unittest.TestCase):
    def test_counts_and_values(self):
        self.assertEqual((len(WEAPONS),len(ARMORS),len(TURRETS)),(20,6,3))
        self.assertEqual(sum(w.price==0 for w in WEAPONS.values()),3)
        self.assertEqual(WEAPONS['W12'].interval,.06)
        self.assertEqual(WEAPONS['W19'].quota,3);self.assertEqual(WEAPONS['W20'].quota,5)
        self.assertEqual(sum(w.category=='rifle' for w in WEAPONS.values()),5)
        for w in WEAPONS:self.assertGreaterEqual(sum(w in a.applicable_weapons for a in ATTACHMENTS.values()),2)
        self.assertEqual(upgrade_cap(99),10);self.assertFalse(applicable_upgrade('W03','range'))
    def test_read_only(self):
        with self.assertRaises(TypeError):WEAPONS['W03']=None

    def test_playtested_starter_damage_and_boss_time(self):
        from air_defense.config import AIRCRAFT
        self.assertEqual(WEAPONS['W17'].base_damage,2)
        self.assertEqual(WEAPONS['W18'].base_damage,5)
        self.assertEqual(AIRCRAFT['ARMORED_BOSS'][1],60)
