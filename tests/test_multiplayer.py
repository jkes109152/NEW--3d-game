import unittest
from uuid import uuid4
from air_defense.multiplayer import CooperativeBattle,party_level,party_multiplier
from air_defense.progression import new_profile,level_for,transact
from air_defense.state import InputFrame
from air_defense.weapons import InputCommand
from air_defense.save_data import validate_profile

class MultiplayerTests(unittest.TestCase):
    def battle(self,count=2):
        members=[dict(id=str(i),name=f'玩家{i}',profile=new_profile()) for i in range(count)]
        return CooperativeBattle(members,level_for(1,1,2),uuid4().hex)
    def test_scaling_and_full_personal_reward(self):
        for count,factor,total,reward in [(1,1,1,125),(2,1.5,2,187),(3,2.25,3,281),(4,3.375,4,421)]:
            level=party_level(level_for(1,1,2),count)
            self.assertEqual(party_multiplier(count),factor)
            self.assertEqual(len(level.roster),total)
            self.assertEqual(level.reward,reward)
    def test_one_world_with_independent_input_and_health(self):
        b=self.battle();other=b.actors['1'];initial=other.player.position
        for _ in range(12):b.advance_group(1/60,{'0':InputFrame(),'1':InputFrame(move_x=1,look_delta=(1,0))})
        self.assertGreater(other.player.position.x,initial.x)
        self.assertEqual(b.player.yaw,0)
        self.assertEqual(other.player.yaw,12)
        self.assertAlmostEqual(b.elapsed,.2)
        self.assertAlmostEqual(next(iter(b.aircraft.values())).elapsed,.2)
        self.assertIs(other.aircraft,b.aircraft)
        other.player.hurt(30);self.assertEqual(b.player.hp,100)
        b.player.hp=0;b.check_outcome();self.assertEqual(b.phase,'active')
        other.player.hp=0;b.check_outcome();self.assertEqual(b.phase,'failure')
    def test_target_destroyed_once_and_shared(self):
        b=self.battle();target=next(iter(b.aircraft))
        b.actors['1'].damage_aircraft(target,99,'guest-shot')
        self.assertEqual(b.aircraft[target].status,'destroyed')
        count=len(b.enemies);b.damage_aircraft(target,99,'host-shot')
        self.assertEqual(len(b.enemies),count)
    def test_personal_ammo_and_lock_do_not_leak(self):
        b=self.battle();other=b.actors['1']
        b.advance_group(1/60,{'1':InputFrame(commands=(InputCommand(1,'select_slot',3),InputCommand(2,'fire_down')),)})
        self.assertEqual(b.player.weapon_slot,1)
        self.assertEqual(other.player.weapon_slot,3)
        self.assertNotEqual(other.runtime[other.active_weapon_id].magazine_rounds,other.stats.magazine_size)
        self.assertFalse(b.held)
    def test_reward_replay_and_tampered_history(self):
        p=new_profile();op=uuid4().hex
        req=dict(kind='coop_reward',profile_id=p['profile_id'],rebirth_count=0,a=1,b=1,A=2,party_size=3)
        transact(p,op,req);transact(p,op,req)
        self.assertEqual(p['coins'],281);validate_profile(p)
        p['operation_history'][0]['summary']['coins_delta']=843
        with self.assertRaises(ValueError):validate_profile(p)
