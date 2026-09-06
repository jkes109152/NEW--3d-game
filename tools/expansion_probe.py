"""公開控制的免費戰役，以及目錄／生命週期證據入口。"""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
import argparse,json,time
from tempfile import TemporaryDirectory
from math import radians,sin,cos
from air_defense.state import AppState,InputFrame
from air_defense.weapons import InputCommand
from air_defense.save_data import SlotRepository
from air_defense.entities import angles,V3
from air_defense.deployment import visible


def play(b,max_seconds=240,observer=None):
    sequence=0;shots={};records=[];target_id=None
    def command(kind,value=None):
        nonlocal sequence
        sequence+=1;return InputCommand(sequence,kind,value)
    for tick in range(int(max_seconds*120)):
        commands=[]
        air=[a for a in b.aircraft.values() if a.hp>sum(m.damage for m in b.missiles.values() if m.target_id==a.id)+1e-9 and a.status=='approaching']
        enemies=[e for e in b.enemies.values() if e.hp>0]
        airborne=next((a for a in air if a.id==target_id),None) or min(air,key=lambda a:(a.remaining,a.id),default=None)
        target=airborne or next((e for e in enemies if e.id==target_id),None) or min(enemies,key=lambda e:((e.position-b.player.position).length(),e.id),default=None)
        move_x=move_z=0.;look=(0,0)
        if target:
            target_id=target.id
            is_air=airborne is not None;distance=(target.center-b.player.eye).length()
            wid='W01' if is_air else 'W03' if distance<23 else 'W17'
            slot=b.loadout.weapon_slots.index(wid)+1
            if b.player.weapon_slot!=slot:commands.append(command('select_slot',slot))
            if is_air and (not b.player.aiming or b.player.weapon_slot!=slot):commands.append(command('toggle_aim'))
            yaw,pitch=angles(target.center-b.player.eye);look=((yaw-b.player.yaw+180)%360-180,pitch-b.player.pitch)
            runtime=b.runtime[wid]
            if runtime.error(b.elapsed) is None and (not is_air or b.lock.ready()):commands.extend((command('fire_up'),command('fire_down')))
            # 有遮蔽時向通道移動；敵兵靠近時沿通道後退，保持真實移速及碰撞。
            danger=min(((e.position-b.player.position).horizontal().length() for e in enemies if e.phase=='ground'),default=999)
            desired=None
            if danger<43:
                nearest=min((e for e in enemies if e.phase=='ground'),key=lambda e:(e.position-b.player.position).horizontal().length());desired=(b.player.position-nearest.position).horizontal()
            elif not is_air and (distance>170 or not visible(b.player.eye,target.center)):desired=V3(-b.player.position.x,0,0)
            if desired:
                v=desired.horizontal().normalized();right=V3(cos(radians(yaw)),0,-sin(radians(yaw)));forward=V3(sin(radians(yaw)),0,cos(radians(yaw)))
                move_x=v.dot(right);move_z=v.dot(forward)
        b.advance(1/120,InputFrame(move_x=move_x,move_z=move_z,look_delta=look,commands=tuple(commands)))
        if observer is not None:observer(b,tuple(b.events),tick)
        for e in b.events:
            if e['kind']=='weapon_fire':shots[e['weapon_id']]=shots.get(e['weapon_id'],0)+1
        if tick%120==0:records.append(dict(time=round(b.elapsed,3),hp=round(b.player.hp,3),city=b.city.hp,air=sum(a.hp>0 for a in b.aircraft.values()),ground=len(b.enemies),position=b.player.position.tuple()))
        if b.phase!='active':break
    return dict(level=b.level.level_id,phase=b.phase,reason=b.failure_reason,seconds=round(b.elapsed,3),shots=shots,hp=b.player.hp,city_hp=b.city.hp,timeline=records,enemy_air_max_hp=[a.max_hp for a in b.aircraft.values()])


def start(app,seed):
    app.begin_preparation()
    for _ in range(3):assert app.next_preparation() is None
    return app.confirm_and_start(seed=seed)


def economy(output,seed=1701):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    result=dict(category='純規則公開移動／視角／有序射擊控制；非原生鍵鼠',seed=seed,levels=[])
    with TemporaryDirectory(prefix='糖果戰役-') as root:
        app=AppState(SlotRepository(root));app.select_slot(1)
        for _ in range(7):
            before=app.profile['coins'];b=start(app,seed);record=play(b);app.settle()
            record.update(coins_before=before,reward=app.profile['coins']-before,coins_after=app.profile['coins']);result['levels'].append(record)
            if b.phase!='success':break
            app.show_menu()
        if len(result['levels'])==7 and all(r['phase']=='success' for r in result['levels']):
            result['rebirth_result']=app.rebirth();b=start(app,seed);result['new_round']=play(b);app.settle()
            result['assets']=dict(coins=app.profile['coins'],owned_weapons=list(app.profile['owned_weapons']),owned_armors=app.profile['owned_armors'],owned_turrets=app.profile['owned_turrets'],player_upgrades=app.profile['player_upgrades'],rebirth_count=app.profile['rebirth_count'])
        result['passed']=len(result['levels'])==7 and all(r['phase']=='success' for r in result['levels']) and result.get('new_round',{}).get('phase')=='success'
        (output/'economy.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({**result,'levels':[{k:v for k,v in r.items() if k!='timeline'} for r in result['levels']]},ensure_ascii=False));return result

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--scenario',choices=['economy','catalog','lifecycle'],default='economy');parser.add_argument('--output',type=Path,default=ROOT/'artifacts'/'002-gameplay-expansion');parser.add_argument('--seed',type=int,default=1701)
    args=parser.parse_args()
    if args.scenario=='economy':raise SystemExit(0 if economy(args.output,args.seed)['passed'] else 1)
    if args.scenario=='lifecycle':
        from tools.engine_probe import run
        run(output=args.output)
    else:
        from dataclasses import asdict
        from air_defense.visual_catalog import RECIPES,ARMOR_PARTS
        from air_defense.catalog import WEAPONS,ARMORS,TURRETS
        args.output.mkdir(parents=True,exist_ok=True)
        evidence={}
        for size in ('1280x720','1920x1080'):
            path=args.output.parent/size/f'{size}-engine-probe.json'
            report=json.loads(path.read_text(encoding='utf-8'));evidence[size]=report['model_identity']
            assert set(evidence[size])==set(WEAPONS)
            assert all(row['preview']==row['battle']==wid for wid,row in evidence[size].items())
        result=dict(category='完整商品能力、輪廓配方與實際引擎共用工廠識別',
            weapons={wid:dict(attributes=asdict(w),silhouette_parts=RECIPES[wid]) for wid,w in WEAPONS.items()},
            armors={aid:dict(attributes=asdict(a),visual_part=ARMOR_PARTS[aid]) for aid,a in ARMORS.items()},
            turrets={tid:asdict(t) for tid,t in TURRETS.items()},model_identity=evidence,passed=True)
        (args.output/'catalog.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        print('目錄 20 武器／6 裝甲／3 砲塔，兩解析度預覽與第一人稱識別全部相符。')
