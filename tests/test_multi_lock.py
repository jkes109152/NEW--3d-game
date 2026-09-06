from tests.fixtures.expansion import owned_weapon
import unittest
from air_defense.state import BattleState
from air_defense.entities import V3
from air_defense.progression import new_profile, level_for

def multi_battle():
    p=new_profile(); p['rebirth_count']=10
    p['owned_weapons']['W02']=owned_weapon();p['confirmed_loadout']['weapon_slots'][4]='W02'
    b=BattleState(p,level_for(12,1,12)); b.player.weapon_slot=5; b.player.aiming=True
    for i,a in enumerate(b.aircraft.values()): a.position=b.player.eye+V3((i-5.5)*3,10,100)
    keys=tuple(b.aircraft); b.lock.update(3,keys,set(keys),True,True,3)
    return b

class MultiLockTests(unittest.TestCase):
    def test_twelve_independent_missiles_once_cooldown(self):
        b=multi_battle()
        self.assertEqual(b.fire(),'applied')
        self.assertEqual(len(b.missiles),12)
        self.assertEqual({m.target_id for m in b.missiles.values()},set(b.aircraft))
        self.assertEqual(b.runtime['W02'].next_shot_at,1.5)

    def test_partial_empty_invalid_and_out_of_range_reject(self):
        for mode in ('partial','empty','dead','range'):
            with self.subTest(mode=mode):
                b=multi_battle()
                if mode=='partial': b.lock.progress[list(b.aircraft)[3]]=.8
                elif mode=='empty': b.lock.clear()
                elif mode=='dead': b.aircraft[list(b.aircraft)[3]].hp=0
                else: b.aircraft[list(b.aircraft)[3]].position=b.player.position+V3(0,10,180.01)
                self.assertNotEqual(b.fire(),'applied')
                self.assertEqual(len(b.missiles),0); self.assertEqual(b.player.cooldowns[5],0)

    def test_partial_factory_failure_rolls_back(self):
        b=multi_battle(); calls=[]
        from air_defense.entities import Missile
        def factory(*args):
            calls.append(args)
            if len(calls)==7: raise RuntimeError('故障注入')
            return Missile(*args)
        b.missile_factory=factory
        self.assertEqual(b.fire(),'launch_failed'); self.assertEqual(b.missiles,{})
        self.assertEqual(b.player.cooldowns[5],0); self.assertTrue(b.lock.ready())
