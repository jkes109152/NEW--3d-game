import unittest
from tempfile import TemporaryDirectory
from air_defense.save_data import SlotRepository
from air_defense.state import AppState

class RestartPersistenceTests(unittest.TestCase):
    def test_only_permanent_state_survives(self):
        with TemporaryDirectory() as root:
            repo=SlotRepository(root); app=AppState(repo); app.select_slot(1)
            app.profile['coins']=1000; app.purchase('rpg'); b=app.start()
            b.player.hp=20; b.player.rpg_ammo=0; b.player.cooldowns[4]=2
            reopened=AppState(SlotRepository(root)); reopened.select_slot(1); fresh=reopened.start()
            self.assertEqual(reopened.profile['coins'],500)
            self.assertEqual((fresh.player.hp,fresh.player.rpg_ammo,fresh.player.cooldowns[4]),(100,3,0))
            self.assertEqual(fresh.lock.progress,{}); self.assertEqual(fresh.missiles,{})
