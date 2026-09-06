import unittest
from air_defense.progression import new_profile
from air_defense.save_data import SlotRepository, validate_profile
from tests.fixtures.expansion import profile, isolated_roots

class ProfileV2Tests(unittest.TestCase):
    def test_new_profile_shape_and_free_inventory(self):
        p=new_profile()
        self.assertEqual(p['schema_version'],2)
        self.assertEqual(len(p),13)
        self.assertEqual(set(p['owned_weapons']),{'W01','W03','W17'})
    def test_roundtrip_and_copy(self):
        p=profile();q=validate_profile(p)
        q['owned_weapons']['W03']['upgrade_levels']['damage']=1
        self.assertEqual(p['owned_weapons']['W03']['upgrade_levels']['damage'],0)
        with isolated_roots() as (new,old):
            old.mkdir();sentinel=old/'slot-1.json';sentinel.write_bytes(b'old data')
            before=sentinel.stat().st_mtime_ns
            repo=SlotRepository(new);repo.save(1,p)
            self.assertEqual(repo.load(1),p)
            self.assertEqual(sentinel.read_bytes(),b'old data');self.assertEqual(sentinel.stat().st_mtime_ns,before)
            with self.assertRaises(ValueError):SlotRepository(old/'nested')
    def test_closed_shape(self):
        for key,value in [('schema_version',1),('schema_version',99),('coins',True),('profile_id','bad')]:
            with self.subTest(key=key,value=value):
                p=profile();p[key]=value
                with self.assertRaises(ValueError):validate_profile(p)

if __name__=='__main__':unittest.main()
