"""實際原生繪製幀時間、壓力計數與硬體證據；不使用估算 FPS。"""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
import argparse
import json
import math
import platform
import time
from air_defense.config import PERFORMANCE


def summarize_frames(seconds):
    if not seconds or any(value<=0 for value in seconds): raise ValueError('幀時間必須為正數')
    ordered=sorted(seconds)
    p99=ordered[min(len(ordered)-1,math.ceil(.99*len(ordered))-1)]
    stalls=[]; consecutive=0
    for index,value in enumerate(seconds):
        consecutive=consecutive+1 if value>.25 else 0
        if consecutive>=2: stalls.append(index)
    mean=len(seconds)/sum(seconds); p1=1/p99
    return {'frames':len(seconds),'seconds':sum(seconds),'average_fps':mean,'p1_fps':p1,'p99_frame_ms':p99*1000,
            'persistent_stall_indices':stalls,'passes':mean>=55 and p1>=45 and not stalls}


def increasing(samples,key):
    values=[row[key] for row in samples]
    return len(values)>1 and values[-1]>values[0] and all(a<=b for a,b in zip(values,values[1:]))


def setup_stress(c,A):
    from air_defense.progression import new_profile,new_weapon,level_for
    from air_defense.state import BattleState
    from air_defense.entities import Enemy,V3
    p=new_profile();p['rebirth_count']=A-2
    for wid in ('W12','W19','W20','W02'):p['owned_weapons'][wid]=new_weapon()
    p['confirmed_loadout']['weapon_slots']=['W01','W12','W19','W20','W02']
    count=12 if A==8 else 4
    for i in range(count):
        key=f'turret-{i:032x}';p['owned_turrets'].append(dict(instance_id=key,turret_id=f'T{i%3+1:02}'))
        p['confirmed_loadout']['deployments'].append(dict(instance_id=key,x=40 if i%2 else -40,z=90+i//2*6))
    b=BattleState(p,level_for(A,1,A));c.state.profile=p;c.state.battle=b;c.state.screen='battle'
    for i in range(12):
        key=f'pressure-{i}';b.enemies[key]=Enemy(key,'GROUND_BOSS' if i%4==0 else 'NORMAL',V3(-12+i%6*5,0,95+i//6*8),phase='ground',effective_max_hp=15)
    b.select_weapon(2);c.ui.show('battle');c.scene.sync(b,0);c.ui.update_hud(b);return b


def run(A=4,warmup=10,duration=60,output=None,await_foreground=False,offscreen=False):
    from tempfile import TemporaryDirectory
    from air_defense.main import create_game
    from air_defense.save_data import SlotRepository
    from air_defense.state import InputFrame
    from air_defense.weapons import InputCommand
    from air_defense.entities import V3,Enemy,angles
    output=Path(output or ROOT/'artifacts'/'002-gameplay-expansion'/'performance');output.mkdir(parents=True,exist_ok=True)
    temporary=TemporaryDirectory(prefix='糖果效能-');repo=SlotRepository(temporary.name)
    if offscreen and await_foreground:raise ValueError('離屏測量不能等待視窗前景')
    engine,c=create_game((1280,720),repository=repo,silent=True,offscreen=offscreen,title=f'糖果防線｜A{A} 效能驗證')
    c.focus_checks=False;c.bridge.update=lambda:None;c.select_slot(1);c.scene.teardown();b=setup_stress(c,A)
    if await_foreground:
        timeout=time.monotonic()+45
        while not engine.win.getProperties().getForeground():
            engine.step()
            if time.monotonic()>timeout:
                c.window_listener.ignoreAll();engine.destroy();temporary.cleanup()
                raise RuntimeError('效能視窗未取得前景；不開始量測')
    frames=[];samples=[];shots={};start=time.perf_counter();last=start;sample_second=-1;hud_elapsed=0;sequence=0;measured_seconds=0.
    def cmd(kind,value=None):
        nonlocal sequence
        sequence+=1;return InputCommand(sequence,kind,value)
    try:
        while True:
            now=time.perf_counter();dt=now-last;last=now;elapsed=now-start
            if measured_seconds>=duration:break
            for i,a in enumerate(b.aircraft.values()):
                if a.hp<=0 or a.elapsed>12:a.hp=a.max_hp;a.status='approaching';a.elapsed=0;a.position=V3((i-(A-1)/2)*10,32,190)
            b.player.hp=b.player.max_hp;b.city.hp=100
            if b.phase!='active':raise AssertionError('壓力情境意外結束')
            whole=int(elapsed)
            if whole!=sample_second:
                sample_second=whole
                for i in range(max(0,12-len(b.enemies))):
                    key=f'wave-{whole}-{i}';b.enemies[key]=Enemy(key,'NORMAL',V3(-12+i%5*5,8,95),source_batch_id='pressure',effective_max_hp=12)
                if elapsed>=warmup:samples.append(dict(second=round(elapsed-warmup,3),foreground=None if offscreen else bool(engine.win.getProperties().getForeground()),missiles=len(b.missiles),rockets=len(b.rockets),enemies=len(b.enemies),aircraft=sum(a.hp>0 for a in b.aircraft.values()),turrets=len(b.turrets),**c.metrics()))
            slot=2 if whole%18<8 else 3 if whole%18<13 else 4
            commands=[]
            if b.player.weapon_slot!=slot:commands.extend((cmd('fire_up'),cmd('select_slot',slot),cmd('fire_down')))
            runtime=b.runtime[b.loadout.weapon_slots[slot-1]]
            # 此為持續負載驅動器，補充火箭配額以在整段量測保持兩種彈體。
            if runtime.quota_remaining==0:runtime.quota_remaining=3;runtime.magazine_rounds=1
            if slot==2 and not b.held:commands.append(cmd('fire_down'))
            elif slot!=2 and runtime.error(b.elapsed) is None:commands.extend((cmd('fire_up'),cmd('fire_down')))
            target=min((e for e in b.enemies.values() if e.hp>0),key=lambda e:(e.position-b.player.position).length(),default=None)
            look=(0,0)
            if target:
                yaw,pitch=angles(target.center-b.player.eye);look=((yaw-b.player.yaw+180)%360-180,pitch-b.player.pitch)
            snap=b.advance(dt,InputFrame(look_delta=look,commands=tuple(commands)))
            for event in snap['events']:
                if event['kind']=='weapon_fire':shots[event['weapon_id']]=shots.get(event['weapon_id'],0)+1
            c.scene.sync(b,dt,snap['events']);hud_elapsed+=dt
            if hud_elapsed>=.05:c.ui.update_hud(b);hud_elapsed=0
            engine.step()
            if elapsed>=warmup:
                frame_seconds=time.perf_counter()-now;frames.append(frame_seconds);measured_seconds+=frame_seconds
        # 等待最後一個已提交的繪製完成，將管線排空時間計入最後一幀。
        drain=time.perf_counter();engine.graphicsEngine.syncFrame()
        if frames:frames[-1]+=time.perf_counter()-drain
        summary=summarize_frames(frames)
        from tools.engine_probe import screenshot
        screenshot(engine,output/f'A{A}-1280x720-medium.png')
        from panda3d.core import ConfigVariableBool,ConfigVariableString
        g=engine.win.getGsg();hardware=dict(platform=platform.platform(),processor=platform.processor(),python=sys.version,renderer=g.getDriverRenderer(),vendor=g.getDriverVendor(),driver=g.getDriverVersion(),sync_video=bool(ConfigVariableBool('sync-video')),threading_model=str(ConfigVariableString('threading-model').getValue()),render_limit_fps=120)
        c.leave_battle()
        for _ in range(4):engine.step()
        cleanup=c.metrics();growth={k:increasing(samples,k) for k in ('missiles','rockets','effects')}
        gate=summary['passes'] if A==4 else True
        result=dict(category='離屏 GPU 實際繪製幀時間' if offscreen else '原生視窗實際繪製幀時間',A=A,resolution=[1280,720],quality='medium',warmup_seconds=warmup,requested_seconds=duration,hardware=hardware,summary=summary,samples=samples,shots=shots,monotonically_increasing=growth,cleanup=cleanup,passes=gate and not any(growth.values()) and cleanup['visuals']==cleanup['effects']==cleanup['active_missiles']==cleanup['active_rockets']==cleanup['core_tracers']==0 and all(shots.get(wid,0)>0 for wid in ('W12','W19','W20')),scenario='補充飛機、敵兵、玩家／城市血量及火箭配額，保持負載；不是通關證據。A4 適用 FPS 門檻；A8 依 SC-011 記錄壓力表現與清理。')
        (output/f'A{A}-frames.json').write_text(json.dumps(frames),encoding='utf-8');(output/f'A{A}-report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(dict(summary=summary,shots=shots,cleanup=cleanup),ensure_ascii=False),flush=True);return result
    finally:c.window_listener.ignoreAll();engine.destroy();temporary.cleanup()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--aircraft',type=int,choices=(4,8),default=4);parser.add_argument('--warmup',type=float,default=10);parser.add_argument('--duration',type=float,default=60);parser.add_argument('--output',type=Path);parser.add_argument('--await-foreground',action='store_true')
    parser.add_argument('--offscreen',action='store_true')
    args=parser.parse_args();result=run(args.aircraft,args.warmup,args.duration,args.output,args.await_foreground,args.offscreen);raise SystemExit(0 if result['passes'] else 1)
