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
    from air_defense.progression import new_profile, caps, level_for
    from air_defense.state import BattleState
    from air_defense.entities import Enemy, V3
    p=new_profile(); r=A-2; p.update(rebirth_count=r,max_aircraft_count=A,upgrade_caps=caps(r))
    p['upgrade_levels'].update(auto_defense=1,auto_defense_capacity=5,multi_anti_aircraft=1)
    p['unlocked_weapons'].append('MULTI_ANTI_AIRCRAFT')
    b=BattleState(p,level_for(A,1,A)); c.state.profile=p; c.state.battle=b; c.state.screen='battle'
    b.player.position=V3(-18,0,70); b.player.pitch=-10; b.player.weapon_slot=5; b.player.aiming=True
    for index in range(12):
        b.enemies[f'pressure-{index}']=Enemy(f'pressure-{index}','GROUND_BOSS' if index%4==0 else 'NORMAL',
                                          V3(-18+(index%6)*6,0,84+index//6*8),phase='ground')
    c.ui.show('battle'); c.scene.sync(b,0); c.ui.update_hud(b)
    return b


def run(A=4,warmup=10,duration=60):
    from air_defense.main import create_game
    from air_defense.save_data import SlotRepository
    from air_defense.state import InputFrame
    from air_defense.entities import V3, Enemy
    output=ROOT/'artifacts'/'performance'; output.mkdir(parents=True,exist_ok=True)
    repo=SlotRepository(ROOT/'artifacts'/'profiles'/f'performance-{A}')
    engine,c=create_game((1280,720),repository=repo,silent=True)
    c.focus_checks=False; c.bridge.update=lambda:None
    c.select_slot(1); c.scene.teardown(); b=setup_stress(c,A)
    frames=[]; samples=[]; start=time.perf_counter(); last=start; sample_second=-1; hud_elapsed=0
    try:
        while True:
            now=time.perf_counter(); dt=now-last; last=now; elapsed=now-start
            if elapsed>warmup+duration: break
            # 固定的負載驅動器補充遭擊落目標，防止 26 秒後空場景冒充 60 秒戰鬥。
            for i,a in enumerate(b.aircraft.values()):
                if a.hp<=0 or a.elapsed>12:
                    a.hp=1; a.status='approaching'; a.elapsed=0; a.position=V3((i-(A-1)/2)*10,32,190)
            b.player.hp=b.player.max_hp; b.city.hp=100
            if b.phase!='active': raise AssertionError('壓力情境意外結束')
            candidates=tuple(a.id for a in b.aircraft.values() if a.hp>0)
            snapshot=b.advance(dt,InputFrame(visible_aircraft=candidates,fire_pressed=b.lock.ready() and b.player.cooldowns[5]<=0))
            # 每秒固定檢查 12 人下限，來源 ID 持續遞增且不重複覆用。
            whole=int(elapsed)
            if whole!=sample_second:
                sample_second=whole
                if len(b.enemies)<12:
                    for i in range(12-len(b.enemies)):
                        key=f'wave-{whole}-{i}'
                        b.enemies[key]=Enemy(key,'NORMAL',V3(-12+i%5*5,8,85),source_batch_id='pressure')
                if elapsed>=warmup:
                    samples.append({'second':round(elapsed-warmup,3),'missiles':len(b.missiles),'effects':len(c.scene.effects),
                                    'enemies':len(b.enemies),'aircraft':len(candidates),'turrets':len(b.turrets)})
            c.scene.sync(b,dt,snapshot['events']); hud_elapsed+=dt
            if hud_elapsed>=.05: c.ui.update_hud(b); hud_elapsed=0
            engine.step()
            if elapsed>=warmup: frames.append(time.perf_counter()-now)
        summary=summarize_frames(frames)
        counts_increasing={key:increasing(samples,key) for key in ('missiles','effects')}
        from tools.engine_probe import screenshot
        screenshot(engine,output/f'A{A}-1280x720-medium.png')
        graphics=engine.win.getGsg()
        hardware={'platform':platform.platform(),'processor':platform.processor(),'python':sys.version,
                  'renderer':graphics.getDriverRenderer(),'vendor':graphics.getDriverVendor(),'driver':graphics.getDriverVersion()}
        c.leave_battle()
        for _ in range(4): engine.step()
        cleanup=c.metrics()
        result={'category':'原生引擎實測','A':A,'resolution':[1280,720],'quality':'medium','warmup_seconds':warmup,
                'requested_seconds':duration,'hardware':hardware,'summary':summary,'samples':samples,
                'monotonically_increasing':counts_increasing,'cleanup':cleanup,
                'passes':summary['passes'] and not any(counts_increasing.values()) and cleanup['visuals']==cleanup['effects']==cleanup['active_missiles']==0,
                'scenario':'實際規則與繪製；負載驅動器維持飛機與敵兵，補滿玩家／城市以持續量測。'}
        (output/f'A{A}-frames.json').write_text(json.dumps(frames),encoding='utf-8')
        (output/f'A{A}-report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(result['summary'],ensure_ascii=False),flush=True)
        return result
    finally:
        c.window_listener.ignoreAll(); engine.destroy()

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--aircraft',type=int,choices=(4,8),default=4)
    parser.add_argument('--warmup',type=float,default=10); parser.add_argument('--duration',type=float,default=60)
    args=parser.parse_args()
    result=run(args.aircraft,args.warmup,args.duration)
    raise SystemExit(0 if result['passes'] else 1)
