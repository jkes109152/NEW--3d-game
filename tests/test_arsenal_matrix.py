"""以商品表固定案例驗收全部武器，避免只驗代表槍種。"""
from copy import deepcopy
from math import ceil
import unittest
from air_defense.catalog import WEAPONS
from air_defense.entities import Enemy,V3,angles
from air_defense.progression import transact
from air_defense.loadout import resolve_weapon_stats
from air_defense.state import InputFrame
from air_defense.weapons import InputCommand
from tests.fixtures.expansion import equipped,profile,owned_weapon,request,operation_id

# 傷害／彈匣／射程直接摘錄 balance.md；霰彈傷害為八彈丸全中。
GROUND_CASES=[('W03',1,12,24),('W04',.65,18,28),('W05',2,8,36),
 ('W06',.6,30,100),('W07',.85,24,120),('W08',1.5,15,150),
 ('W09',1,20,110),('W10',.45,40,80),('W11',.45,24,36),
 ('W12',.4,32,30),('W13',.7,27,45),('W14',.9,20,42),
 ('W15',3.2,6,18),('W16',2.4,8,15),('W17',2,5,180),
 ('W18',5,4,210),('W19',35,1,60),('W20',22,1,90)]


class ArsenalMatrixTests(unittest.TestCase):
    def test_eighteen_ground_weapons_hit_and_spend_exactly_one_round(self):
        for wid,damage,magazine,distance in GROUND_CASES:
            with self.subTest(weapon=wid):
                b=equipped(wid);b.player.position=V3(40,0,100)
                enemy=Enemy('matrix-target','NORMAL',V3(40,0,102),phase='ground',effective_max_hp=100)
                b.enemies={enemy.id:enemy};b.player.yaw,b.player.pitch=angles(enemy.center-b.player.eye)
                self.assertEqual(b.stats.range,distance);self.assertEqual(b.fire(),'applied')
                self.assertEqual(b.runtime[wid].magazine_rounds,magazine-1)
                if wid in ('W19','W20'):
                    self.assertEqual(len(b.rockets),1)
                    for _ in range(12):b.advance(1/120)
                    self.assertEqual(len(b.rockets),0)
                self.assertAlmostEqual(enemy.hp,100-damage)
                self.assertEqual(b.shot_number,1)

    def test_all_ground_modes_air_shot_reload_pause_and_switch(self):
        # 0.3 秒內的長按發數；半自動與上膛均只有一次，三連發均恰三次。
        counts=[1,3,1,3,3,1,2,4,4,5,3,2,1,1,1,1,1,1]
        for (wid,_,magazine,_),count in zip(GROUND_CASES,counts):
            with self.subTest(weapon=wid):
                b=equipped(wid);b.player.pitch=-60
                for i in range(36):b.advance(1/120,InputFrame(commands=(InputCommand(1,'fire_down'),) if i==0 else ()))
                self.assertEqual(b.shot_number,count)
                r=b.runtime[wid];self.assertEqual(r.magazine_rounds,magazine-count)
                b.advance(1/120,InputFrame(commands=(InputCommand(2,'fire_up'),InputCommand(3,'reload'))))
                deadline=r.reload_finish_at;self.assertIsNotNone(deadline)
                frozen=deepcopy(r);elapsed=b.elapsed;b.pause()
                for _ in range(3):b.advance(1)
                self.assertEqual(b.elapsed,elapsed);self.assertEqual(r,frozen)
                b.resume();b.advance(1/120,InputFrame(commands=(InputCommand(4,'fire_up'),)))
                while b.elapsed+1/120<deadline-1e-8:b.advance(1/120)
                self.assertNotEqual(r.magazine_rounds,magazine)
                b.advance(1/120);self.assertEqual(r.magazine_rounds,magazine)
                before=deepcopy(r);b.select_weapon(1);b.select_weapon(2)
                self.assertEqual(r.magazine_rounds,before.magazine_rounds)
                self.assertEqual(r.quota_remaining,before.quota_remaining)
                self.assertGreaterEqual(r.next_shot_at,before.next_shot_at)
                self.assertEqual(b.shot_number,count)

    def test_both_anti_air_lock_and_fixed_launch_snapshot(self):
        for wid,wanted in [('W01',1),('W02',2)]:
            with self.subTest(weapon=wid):
                b=equipped(wid);a=next(iter(b.aircraft.values()));a.position=V3(40,20,140)
                twin=deepcopy(a);twin.id='second';twin.position=V3(41,20,140);b.aircraft[twin.id]=twin
                b.player.position=V3(40,0,100);b.player.yaw,b.player.pitch=angles(a.center-b.player.eye)
                self.assertEqual(b.fire(),'lock');self.assertFalse(b.reload())
                b.player.aiming=True;b.lock.update(3,tuple(b.aircraft),set(b.aircraft),True,wid=='W02',3)
                self.assertEqual(b.fire(),'applied');self.assertEqual(len(b.missiles),wanted)
                snapshots={m.target_id:m.damage for m in b.missiles.values()}
                self.assertEqual(set(snapshots.values()),{1})
                b.pause();before=[m.position for m in b.missiles.values()];b.advance(1)
                self.assertEqual([m.position for m in b.missiles.values()],before)
                b.resume();b.select_weapon(2 if wid=='W01' else 3)
                self.assertEqual({m.target_id:m.damage for m in b.missiles.values()},snapshots)

    def test_twenty_weapons_upgrade_customize_isolation_caps_and_replay(self):
        for wid in WEAPONS:
            with self.subTest(weapon=wid):
                p=profile(coins=50000);p['owned_weapons']={key:owned_weapon() for key in WEAPONS}
                untouched={key:deepcopy(value) for key,value in p['owned_weapons'].items() if key!=wid}
                sequence=0
                def buy(kind,**fields):
                    nonlocal sequence
                    sequence+=1;return transact(p,operation_id(sequence),request(p,kind,weapon_id=wid,**fields))
                for _ in range(5):self.assertEqual(buy('upgrade_weapon',upgrade_id='damage')['result_code'],'applied')
                self.assertEqual(buy('upgrade_weapon',upgrade_id='damage')['reason'],'cap_reached')
                self.assertEqual(buy('purchase_attachment',attachment_id='heavy_barrel')['result_code'],'applied')
                self.assertEqual(buy('purchase_cosmetic',cosmetic_kind='color',cosmetic_id='mint')['result_code'],'applied')
                fields=dict(selected_attachments=dict(optic=None,barrel='heavy_barrel',feed=None),selected_color='mint',selected_pattern='plain')
                self.assertEqual(buy('customize_weapon',**fields)['coins_delta'],0)
                req=request(p,'customize_weapon',weapon_id=wid,**fields);before=deepcopy(p)
                replay=transact(p,operation_id(sequence),req)
                self.assertEqual(replay['result_code'],'applied');self.assertEqual(p,before)
                self.assertEqual({key:value for key,value in p['owned_weapons'].items() if key!=wid},untouched)
                self.assertAlmostEqual(resolve_weapon_stats(p,wid).base_damage,WEAPONS[wid].base_damage*2.25*1.15)
                illegal='extended_magazine' if wid in ('W01','W02','W19','W20') else 'cooling_guidance'
                self.assertEqual(buy('purchase_attachment',attachment_id=illegal)['reason'],'incompatible')
                p['coins']=0
                self.assertEqual(buy('purchase_cosmetic',cosmetic_kind='pattern',cosmetic_id='dots')['reason'],'insufficient_coins')
