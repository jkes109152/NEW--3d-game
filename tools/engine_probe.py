"""新版引擎畫面／生命週期情境；測試配置不冒充真實鍵鼠或通關。"""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
import argparse
import json
from tempfile import TemporaryDirectory
from unittest.mock import patch
from air_defense.main import create_game
from air_defense.save_data import SlotRepository, SaveError
from air_defense.entities import V3, Enemy, angles
from air_defense.catalog import WEAPONS, ARMORS, TURRETS


def screenshot(engine,path):
    from panda3d.core import Filename
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    for _ in range(4):engine.step()
    if not engine.win.saveScreenshot(Filename.fromOsSpecific(str(path.resolve()))):raise RuntimeError('截圖保存失敗')


def start(c,slots=None):
    c.start()
    if slots:c.state.draft.loadout['weapon_slots']=list(slots)
    for _ in range(3):c.prep_next()
    c.confirm_start();c.release_mouse()
    assert c.state.battle is not None
    return c.state.battle


def run(size=(1280,720),output=None,offscreen=True,scenario='expansion'):
    output=Path(output or ROOT/'artifacts'/'002-gameplay-expansion'/'screens');output.mkdir(parents=True,exist_ok=True)
    with TemporaryDirectory(prefix='糖果畫面-') as folder:
        repo=SlotRepository(folder)
        engine,c=create_game(size,repository=repo,silent=True,offscreen=offscreen)
        c.focus_checks=False;c.bridge.update=lambda:None
        label=f'{size[0]}x{size[1]}';shots=[];results={};identities={}
        def shot(name):
            screenshot(engine,output/f'{label}-{name}.png');shots.append(name)
        try:
            shot('slot-select');c.select_slot(1);shot('profile-menu')
            # 商品畫面使用隔離的高餘額配置；所有商品仍經正常交易入口。
            c.state.profile['coins']=100000;c.state.profile['rebirth_count']=6
            repo.save(1,c.state.profile)
            for wid in WEAPONS:
                if wid not in c.state.profile['owned_weapons']:assert c.state.transaction('purchase_weapon',weapon_id=wid)['result_code']=='applied'
            for aid in ARMORS:assert c.state.transaction('purchase_armor',armor_id=aid)['result_code']=='applied'
            for tid in TURRETS:
                for _ in range(4):assert c.state.transaction('purchase_turret',turret_id=tid)['result_code']=='applied'
            for category in ('player','armor','turret','weapon'):
                c.store_select(category);shot('store-'+category)
            for page in range(1,4):c.store_select(page=page);shot('store-weapons-'+str(page+1))
            for wid in WEAPONS:
                c.customize(wid);shot('custom-'+wid);identities[wid]={'preview':c.ui.preview.weapon_id}
            c.customize('W17');c.customize_tab('attachment');shot('custom-attachments')
            c.shop_action('purchase_attachment',weapon_id='W17',attachment_id='zoom_scope')
            c.custom_select('selected_attachments','zoom_scope','optic');c.apply_custom()
            c.customize_tab('appearance');shot('custom-appearance')
            c.back();c.back();c.start();shot('prepare-armor')
            c.prep_armor('A06');c.prep_next();shot('prepare-weapons');c.prep_next();shot('prepare-deployment')
            from ursina import camera
            center=c.scene.ground_point((0,0));right=c.scene.ground_point((.1,0));up=c.scene.ground_point((0,.1))
            results['projection']={'center':None if center is None else center.tuple(),'right':None if right is None else right.tuple(),'up':None if up is None else up.tuple()}
            assert center is not None and abs(center.x)<1e-3 and abs(center.z-80)<1e-3,results['projection']
            assert abs(right.x-center.x-20)<.001 and abs(up.z-center.z-20)<.001,results['projection']
            tower=c.state.profile['owned_turrets'][0]['instance_id'];assert c.state.place_turret(tower,40,70) is None
            c.deploy_select(tower);shot('deployment-selected');c.prep_next();shot('prepare-confirm')
            with patch.object(repo,'save',side_effect=SaveError('write_failed','故障注入')):c.confirm_start()
            assert c.state.pending_save and c.state.battle is None;shot('save-error');c.retry_save()
            assert c.state.screen=='prepare_confirm' and c.state.battle is None
            c.confirm_start();c.release_mouse();b=c.state.battle;c.scene.sync(b,0);c.ui.update_hud(b);shot('battle-hud')
            b.select_weapon(3);b.fire();c.scene.sync(b,.001,b.events);c.ui.update_hud(b);shot('battle-fire')
            b.reload();c.scene.sync(b,.1,b.events);c.ui.update_hud(b);shot('battle-reload')
            c.pause();shot('pause');c.open_settings();shot('settings');c.back();c.resume()
            b.fail('impact');c.state.settle();c.ui.show();shot('result-failure');c.show_menu();c.request_rebirth();shot('rebirth-confirm');c.back()
            b=start(c)
            for a in b.aircraft.values():a.status='destroyed';a.hp=0
            b.check_outcome();c.state.settle();c.ui.show();shot('result-success');c.show_menu()
            c.request_delete(1);shot('delete-confirm');c.back();c.select_slot(1)
            for wid in WEAPONS:
                c.start();c.state.draft.loadout['weapon_slots']=['W01',wid,'W03',None,None] if wid=='W02' else ['W01',wid,None,None,None] if wid!='W01' else ['W01','W03',None,None,None]
                for _ in range(3):c.prep_next()
                c.confirm_start();c.release_mouse();b=c.state.battle;b.select_weapon(1 if wid=='W01' else 2)
                if wid in ('W01','W02'):
                    a=next(iter(b.aircraft.values()));b.player.yaw,b.player.pitch=angles(a.position-b.player.eye);b.player.aiming=True
                    b.lock.update(3,b.candidates(),set(b.aircraft),True,wid=='W02',3)
                b.fire();c.scene.sync(b,.001,b.events);c.ui.update_hud(b);shot('battle-'+wid)
                identities[wid]['battle']=c.scene.weapon.gun.weapon_id
                assert identities[wid]['preview']==identities[wid]['battle']==wid
                c.leave_battle()
            for _ in range(4):engine.step()
            from air_defense.models import cache_metrics
            baseline=c.metrics();cache_baseline=cache_metrics();cycles=[]
            for i in range(10):
                b=start(c,('W01','W17','W03','W19','W20'));b.select_weapon(3);b.fire();b.select_weapon(4);b.fire();c.scene.sync(b,.01,b.events)
                c.pause();c.resume();b.fail('player');c.state.settle();c.ui.show();c.show_menu()
                for _ in range(4):engine.step()
                cycles.append(c.metrics())
            keys=('visuals','effects','engine_entities','engine_tasks','input_handlers','lock_markers','active_missiles','active_rockets','pending_commands','core_tracers','ui_layers','ui_buttons')
            differences={key:cycles[-1][key]-baseline[key] for key in keys}
            results.update(category='引擎 API 情境（非原生輸入／通關證據）',offscreen=offscreen,resolution=size,screenshots=shots,model_identity=identities,baseline=baseline,cycles=cycles,active_differences=differences,cache_baseline=cache_baseline,cache_after=cache_metrics())
            (output/f'{label}-engine-probe.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
            assert not any(differences.values()),differences
            assert cache_baseline==cache_metrics(), '暖機後快取仍持續增加'
            print(json.dumps(results,ensure_ascii=False));return results
        finally:c.window_listener.ignoreAll();engine.destroy()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--size',default='1280x720');parser.add_argument('--output',type=Path);parser.add_argument('--scenario',choices=('expansion',),default='expansion');parser.add_argument('--onscreen',action='store_true')
    args=parser.parse_args();run(tuple(map(int,args.size.split('x'))),args.output,not args.onscreen,args.scenario)
