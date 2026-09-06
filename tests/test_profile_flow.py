import unittest
from tempfile import TemporaryDirectory
from air_defense.save_data import SlotRepository

class ProfileFlowTests(unittest.TestCase):
    def test_five_slots_create_summary_cancel_and_repeated_delete(self):
        with TemporaryDirectory() as root:
            repo=SlotRepository(root)
            for slot in range(1,6):
                p=repo.create(slot); p['coins']=slot*100; repo.save(slot,p)
            self.assertEqual([p['coins'] for _,p,_ in repo.list_slots()],[100,200,300,400,500])
            token=repo.request_delete(3); repo.cancel_delete(token)
            self.assertFalse(repo.confirm_delete(3,token))
            token=repo.request_delete(3)
            self.assertFalse(repo.confirm_delete(2,token))
            self.assertTrue(repo.confirm_delete(3,token))
            self.assertFalse(repo.confirm_delete(3,token))
            self.assertIsNone(repo.load(3)); self.assertEqual(repo.load(4)['coins'],400)
