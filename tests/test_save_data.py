import json
import tempfile
import unittest
from unittest.mock import patch
from air_defense.save_data import SlotRepository, SaveError, validate_profile
from air_defense.progression import new_profile


class SaveTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.repo=SlotRepository(self.tmp.name)

    def test_T19_isolation_corruption_and_delete(self):
        a=self.repo.create(1); b=self.repo.create(2)
        a['coins']=45; self.repo.save(1,a)
        self.assertEqual(self.repo.load(2)['coins'],0)
        token=self.repo.request_delete(1)
        self.assertFalse(self.repo.confirm_delete(2,token))
        self.assertTrue(self.repo.confirm_delete(1,token))
        self.assertFalse(self.repo.confirm_delete(1,token))
        self.assertIsNotNone(self.repo.load(2))
        raw=b'{broken'
        self.repo.path(3).write_bytes(raw)
        with self.assertRaises(SaveError): self.repo.load(3)
        self.assertEqual(self.repo.path(3).read_bytes(),raw)
        self.repo.recover(3,confirm=True)
        self.assertEqual(list(self.repo.root.glob('slot-3.corrupt.*.json'))[0].read_bytes(),raw)

    def test_strict_schema(self):
        for key,value in [('coins',True),('coins',-1),('schema_version',99),('rebirth_count',1.5),('extra',0)]:
            p=new_profile(); p[key]=value
            with self.assertRaises(ValueError): validate_profile(p)

    def test_T20_atomic_retry(self):
        p=self.repo.create(1); p['coins']=1000; self.repo.save(1,p)
        before=self.repo.path(1).read_bytes()
        req={'kind':'upgrade_player','upgrade_id':'max_hp','profile_id':p['profile_id'],'rebirth_count':0}
        with patch('air_defense.save_data.os.replace',side_effect=OSError('fault')):
            with self.assertRaises(SaveError): self.repo.transaction(1,p,'1'*32,req)
        self.assertEqual(p['coins'],750)
        self.assertEqual(self.repo.path(1).read_bytes(),before)
        self.repo.save(1,p)
        self.assertEqual(self.repo.load(1)['coins'],750)
        self.repo.transaction(1,self.repo.load(1),'1'*32,req)
        self.assertEqual(self.repo.load(1)['coins'],750)
