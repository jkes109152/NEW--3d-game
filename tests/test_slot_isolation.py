import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from concurrent.futures import ThreadPoolExecutor
from air_defense.save_data import SlotRepository

class SlotIsolationTests(unittest.TestCase):
    def test_alternating_writes_delete_only_owned_backups(self):
        with TemporaryDirectory() as root:
            repo=SlotRepository(root)
            for slot in range(1,6):
                p=repo.create(slot); p['coins']=slot; repo.save(slot,p)
                (Path(root)/f'slot-{slot}.corrupt.20260905T000000Z.json').write_bytes(bytes([slot]))
            token=repo.request_delete(2); repo.confirm_delete(2,token)
            self.assertEqual(len(list(Path(root).glob('*.corrupt.*'))),4)
            self.assertEqual(repo.load(1)['coins'],1)
            self.assertIsNone(repo.load(2)); self.assertEqual(repo.load(5)['coins'],5)

    def test_concurrent_reads_only_observe_complete_profiles(self):
        with TemporaryDirectory() as root:
            repo=SlotRepository(root); p=repo.create(1)
            def write():
                for n in range(25): p['coins']=n; repo.save(1,p)
            def read(): return [repo.load(1)['coins'] for _ in range(25)]
            with ThreadPoolExecutor(max_workers=2) as pool:
                writer=pool.submit(write); reader=pool.submit(read)
                writer.result(); values=reader.result()
            self.assertTrue(all(type(value) is int for value in values))
