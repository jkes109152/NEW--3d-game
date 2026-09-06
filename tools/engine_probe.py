"""原生引擎自動情境；與真人式 SendInput 驗收分開記錄。"""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
import argparse
import json
from math import atan2, degrees
from air_defense.main import create_game
from air_defense.save_data import SlotRepository
from air_defense.progression import caps, level_for, new_profile
from air_defense.state import BattleState, InputFrame
from air_defense.entities import Enemy, V3, angles


def screenshot(engine,path):
    from panda3d.core import Filename
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    for _ in range(4): engine.step()
    if not engine.win.saveScreenshot(Filename.fromOsSpecific(str(path.resolve()))): raise RuntimeError('截圖保存失敗')


def run(size=(1280,720),output=None):
    output=Path(output or ROOT/'artifacts'/'us6'); output.mkdir(parents=True,exist_ok=True)
    repo=SlotRepository(ROOT/'artifacts'/'profiles'/f'engine-{size[0]}')
    # 此目錄只由工具建立；每次使用固定初始資料。
    repo.save(1,new_profile())
    engine,c=create_game(size,repository=repo,silent=True)
    c.focus_checks=False; c.bridge.update=lambda:None
    records=[]; label=f'{size[0]}x{size[1]}'
    def shot(name): screenshot(engine,output/f'{label}-{name}.png')
    try:
        shot('slot-select')
        c.select_slot(1); shot('profile-menu')
        c.state.profile['coins']=30000
        c.route('store'); shot('store')
        for key in ('rpg','auto_defense','multi_anti_aircraft'): c.purchase(key)
        c.route('profile_menu'); c.start(); b=c.state.battle
        c.release_mouse()
        c.scene.sync(b,0); c.ui.update_hud(b); shot('battle-hud')
        target=b.aircraft['air-0']; yaw,pitch=angles(target.position-b.player.eye)
        b.player.yaw=yaw; b.player.pitch=pitch; b.player.aiming=True
        for _ in range(360):
            # 控制目標保持鏡頭中央，驗證真正 LockState 計時。
            yaw,pitch=angles(target.position-b.player.eye)
            b.player.yaw=yaw; b.player.pitch=pitch
            b.advance(1/120,InputFrame())
        assert b.lock.ready()
        c.scene.sync(b,0); c.ui.update_hud(b); shot('single-lock')
        assert b.fire()=='applied'
        records.extend(b.events)
        for _ in range(300):
            snapshot=b.advance(1/120,InputFrame())
            records.extend(snapshot['events'])
            if target.hp<=0: break
        assert target.hp==0
        c.scene.sync(b,.01,records[-6:]); c.ui.update_hud(b); shot('aircraft-destroyed')
        c.pause(); shot('pause')
        c.open_settings(); shot('settings'); c.back(); c.resume()
        c.leave_battle()
        # 固定支援飛機情境，確保下降人物與空地混合畫面必定存在。
        c.state.cursor=(2,3); c.start(); b=c.state.battle; c.release_mouse()
        b.aircraft['air-0'].position=V3(-10,10,100)
        b.damage_aircraft('air-0',1); records.extend(b.events)
        b.player.yaw=8; b.player.pitch=-5
        c.scene.sync(b,0,b.events); c.ui.update_hud(b); shot('mixed-descent')
        for _ in range(480): b.advance(1/120,InputFrame())
        c.scene.sync(b,.01); c.ui.update_hud(b); shot('mixed-ground')
        for a in b.aircraft.values():
            if a.hp>0: b.damage_aircraft(a.id,a.hp)
        for e in list(b.enemies.values()): b.damage_enemy(e.id,e.hp)
        b.check_outcome(); c.state.settle(); c.release_mouse(); c.ui.show(); shot('result-success')
        c.show_menu(); c.start(); b=c.state.battle; b.fail('impact'); c.state.settle(); c.release_mouse(); c.ui.show(); shot('result-failure')
        c.show_menu(); c.request_rebirth(); shot('rebirth-confirm'); c.confirm_rebirth(); shot('rebirth-menu')
        # 十二架飛機透過規則進度與同一攻擊入口齊射。
        p=new_profile(); p.update(rebirth_count=10,max_aircraft_count=12,upgrade_caps=caps(10))
        p['upgrade_levels']['multi_anti_aircraft']=1; p['unlocked_weapons'].append('MULTI_ANTI_AIRCRAFT')
        b=BattleState(p,level_for(12,1,12)); c.state.battle=b; c.state.screen='battle'
        c.scene.teardown(); c.ui.show('battle'); b.player.weapon_slot=5; b.player.aiming=True
        for i,a in enumerate(b.aircraft.values()): a.position=b.player.eye+V3((i-5.5)*3,10,110)
        b.lock.update(3,tuple(b.aircraft),set(b.aircraft),True,True,3)
        c.scene.sync(b,0); c.ui.update_hud(b); shot('multi-lock-12')
        assert b.fire()=='applied' and len(b.missiles)==12
        records.extend(b.events)
        for _ in range(25):
            snapshot=b.advance(1/120,InputFrame())
            c.scene.sync(b,1/120,snapshot['events'])
        c.ui.update_hud(b); shot('multi-salvo')
        c.leave_battle()
        # 相同主選單比較十次清理；固定資源池另列，不算活動實體。
        for _ in range(4): engine.step()
        baseline=c.metrics(); cycles=[]
        for index in range(10):
            c.start(); b=c.state.battle
            b.damage_aircraft('air-0',1)
            c.scene.sync(b,.01,b.events)
            c.leave_battle()
            for _ in range(4): engine.step()
            cycles.append(c.metrics())
        active=('visuals','effects','engine_entities','engine_tasks','input_handlers','lock_markers','active_missiles')
        differences={key:cycles[-1][key]-baseline[key] for key in active}
        result={'category':'原生引擎自動情境','resolution':size,'profile_root':str(repo.root),
                'baseline':baseline,'cycles':cycles,'active_differences':differences,'events':records,'exit_code':0}
        (output/f'{label}-engine-probe.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        if any(differences.values()): raise AssertionError(f'生命週期計數未歸零：{differences}')
        print(json.dumps({'resolution':size,'active_differences':differences,'screenshots':len(list(output.glob(label+'-*.png')))},ensure_ascii=False))
        return result
    finally:
        c.window_listener.ignoreAll(); engine.destroy()

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--size',default='1280x720')
    args=parser.parse_args()
    run(tuple(map(int,args.size.split('x'))))
