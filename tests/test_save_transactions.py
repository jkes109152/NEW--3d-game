import unittest
from tempfile import TemporaryDirectory
from unittest.mock import patch
from pathlib import Path
from air_defense.save_data import SlotRepository, SaveError
from air_defense.state import AppState

class SaveTransactionTests(unittest.TestCase):
    def test_pending_purchase_blocks_more_transactions_until_retry(self):
        with TemporaryDirectory() as root:
            repo=SlotRepository(root); app=AppState(repo); app.select_slot(1); app.profile['coins']=1000; repo.save(1,app.profile)
            with patch('air_defense.save_data.os.replace',side_effect=PermissionError('故障注入')):
                self.assertEqual(app.purchase('max_hp','same'),'save_failed')
            self.assertEqual(app.profile['coins'],750); self.assertTrue(app.pending_save)
            self.assertEqual(app.purchase('max_hp','other'),'phase'); self.assertIsNone(app.start())
            self.assertTrue(app.retry_save()); self.assertEqual(repo.load(1)['coins'],750)
            restarted=repo.load(1)
            repo.transaction(1,restarted,'same',{'kind':'purchase','upgrade_id':'max_hp'})
            self.assertEqual(restarted['coins'],750); self.assertEqual(restarted['profile_revision'],1)

    def test_backup_failure_never_replaces_original(self):
        with TemporaryDirectory() as root:
            repo=SlotRepository(root); repo.path(1).write_bytes(b'invalid')
            original=Path.open
            def fail_backup(path,*args,**kwargs):
                if '.corrupt.' in path.name: raise PermissionError('故障注入')
                return original(path,*args,**kwargs)
            with patch.object(Path,'open',fail_backup):
                with self.assertRaises(SaveError) as error: repo.recover(1,True)
            self.assertEqual(error.exception.code,'backup_failed'); self.assertEqual(repo.path(1).read_bytes(),b'invalid')
