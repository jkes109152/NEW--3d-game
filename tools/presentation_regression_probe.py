"""最後呈現修正的離屏重驗；獨立圖形配置，不操作使用者桌面。"""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
import argparse,json
from tempfile import TemporaryDirectory
from air_defense.main import create_game
from air_defense.save_data import SlotRepository
from air_defense.entities import Enemy,V3
from tools.engine_probe import screenshot
from tools.review_engine_probe import assert_effective_shader


def run(size):
    output=ROOT/'artifacts'/'002-gameplay-expansion'/'presentation-final';output.mkdir(exist_ok=True)
    label=f'{size[0]}x{size[1]}'
    with TemporaryDirectory(prefix='糖果呈現複驗-') as folder:
        engine,c=create_game(size,offscreen=True,silent=True,repository=SlotRepository(folder));c.bridge.update=lambda:None;c.focus_checks=False
        try:
            c.select_slot(1);c.state.profile.update(coins=100000,rebirth_count=1)
            preview_bounds=[]
            for number in range(1,21):
                wid=f'W{number:02}'
                if wid not in c.state.profile['owned_weapons']:c.state.transaction('purchase_weapon',weapon_id=wid)
                c.customize(wid);pivot=c.ui.preview;pivot.preview_zoom=1
                for angle in range(0,360,30):
                    pivot.rotation_y=angle;c.ui.frame_preview(pivot);low,high=pivot.getTightBounds(c.ui.layer)
                    assert low.x>=-.771 and high.x<=-.169 and low.y>=-.266 and high.y<=-.044,(wid,angle,low,high)
                    preview_bounds.append(dict(weapon_id=wid,rotation=angle,minimum=tuple(low),maximum=tuple(high)))
                pivot.rotation_y=-110;c.ui.frame_preview(pivot)
                if wid in ('W01','W02','W11','W18'):screenshot(engine,output/f'{label}-custom-{wid}.png')
            from air_defense.models import sphere_mesh
            sphere=sphere_mesh();low,high=sphere.getTightBounds()
            assert all(abs(value+.5)<1e-6 for value in low) and all(abs(value-.5)<1e-6 for value in high),'合併商品污染球體模板'
            sphere.removeNode()
            c.show_menu();c.state.transaction('purchase_turret',turret_id='T01');c.start();c.prep_next();c.prep_next()
            key=c.state.profile['owned_turrets'][0]['instance_id'];assert c.state.place_turret(key,40,70) is None
            c.deploy_select(key);screenshot(engine,output/f'{label}-deployment-selected.png');print('部署截圖完成',flush=True);c.prep_next();c.confirm_start();c.release_mouse();print('進入戰鬥',flush=True)
            b=c.state.battle;b.aircraft.clear();b.player.position=V3(0,0,100)
            for index,kind in enumerate(('NORMAL','GROUND_BOSS')):
                key=f'actor-{index}';b.enemies[key]=Enemy(key,kind,V3(-2+index*4,0,108),phase='ground')
            c.scene.sync(b,0);c.ui.update_hud(b);print('角色建立完成',flush=True)
            screenshot(engine,output/f'{label}-actors-created.png')
            from panda3d.core import GeomVertexReader
            geometry=[]
            for node in c.scene.visuals['actor-0'].findAllMatches('**/+GeomNode'):
                data=node.node().getGeom(0).getVertexData();row={'format':str(data.getFormat()),'path':str(node),'bounds':str(node.getTightBounds(c.scene.visuals['actor-0'])),'transform':str(node.getNetTransform())}
                if data.hasColumn('normal'):
                    reader=GeomVertexReader(data,'normal');row['normal']=tuple(reader.getData3())
                    reader.clear()
                geometry.append(row)
            (output/f'{label}-geometry.json').write_text(json.dumps(geometry,ensure_ascii=False,indent=2),encoding='utf-8')
            quality_checks=[]
            for index,quality in enumerate(('low','medium','high','low','high','medium')):
                print('切換畫質',quality,flush=True)
                c.settings.quality=quality;c.apply_settings()
                key=f'new-{index}';b.enemies[key]=Enemy(key,'NORMAL',V3(-4+index,0,115),phase='ground');c.scene.sync(b,0)
                for root in (c.scene.root,c.scene.dynamic,c.scene.weapon):assert_effective_shader(root,c.scene.shader._shader)
                assert c.scene.shadows_enabled==(quality!='low') and c.scene.sun._light.isActive()==(quality!='low')
                screenshot(engine,output/f'{label}-actors-{quality}.png')
                quality_checks.append(dict(quality=quality,shadows_enabled=c.scene.shadows_enabled,new_actor=key,shader=c.scene.shader.name))
            c.leave_battle()
            for _ in range(4):engine.step()
            cleanup=c.metrics();assert all(cleanup[key]==0 for key in ('visuals','effects','active_missiles','active_rockets','core_tracers','pending_commands'))
            report=dict(category='離屏引擎呈現回歸；隔離商品與靜態敵兵配置，不代表原生鍵鼠或通關',resolution=size,preview_bounds=preview_bounds,geometry=geometry,quality_checks=quality_checks,cleanup=cleanup,passed=True)
            (output/f'{label}-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
            print(label,'呈現複驗完成。')
        finally:c.window_listener.ignoreAll();engine.destroy()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--size',default='1280x720');args=parser.parse_args();run(tuple(map(int,args.size.split('x'))))
