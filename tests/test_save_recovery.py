import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from air_defense.save_data import SlotRepository, SaveError, validate_profile
from air_defense.progression import new_profile

class SaveRecoveryTests(unittest.TestCase):
    def test_raw_invalid_utf8_backup_and_rebuild(self):
        with TemporaryDirectory() as root:
            repo=SlotRepository(root); raw=b'\xff\xfe damaged\x00'
            repo.path(1).write_bytes(raw)
            with self.assertRaises(SaveError) as error: repo.load(1)
            self.assertEqual(error.exception.code,'corrupt')
            self.assertIsNone(repo.recover(1,False)); self.assertEqual(repo.path(1).read_bytes(),raw)
            repo.recover(1,True)
            self.assertEqual(next(Path(root).glob('slot-1.corrupt.*.json')).read_bytes(),raw)
            self.assertEqual(repo.load(1)['coins'],0)

    def test_closed_schema_unknown_version_negative_and_wrong_types(self):
        for key,value in (('schema_version',99),('coins',-1),('coins',True),('rebirth_available',1),('operation_history',{})):
            p=new_profile(); p[key]=value
            with self.assertRaises(ValueError): validate_profile(p)
        p=new_profile(); p['unknown']=1
        with self.assertRaises(ValueError): validate_profile(p)

    def test_failed_replace_keeps_formal_bytes_and_removes_temporary(self):
        with TemporaryDirectory() as root:
            repo=SlotRepository(root); p=repo.create(1); before=repo.path(1).read_bytes(); p['coins']=8
            with patch('air_defense.save_data.os.replace',side_effect=PermissionError('故障注入')):
                with self.assertRaises(SaveError): repo.save(1,p)
            self.assertEqual(repo.path(1).read_bytes(),before)
            self.assertEqual(list(Path(root).glob('*.tmp')),[])
