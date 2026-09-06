"""原生鍵鼠驗收宿主：隔離資料、持續記錄真正引擎 input，不自動操作介面。"""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from tempfile import TemporaryDirectory
import argparse,json,time
from air_defense.main import create_game
from air_defense.save_data import SlotRepository
from air_defense.progression import new_profile,new_weapon
OUTPUT=ROOT/'artifacts'/'002-gameplay-expansion'/'native-input.json'

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--equipped',action='store_true');parser.add_argument('--output',type=Path,default=OUTPUT);parser.add_argument('--time-scale',type=float,default=1);args=parser.parse_args()
    if not 0<args.time_scale<=1:parser.error('time-scale 必須大於零且不超過一')
    with TemporaryDirectory(prefix='糖果原生驗證-') as root:
        repo=SlotRepository(root);p=new_profile();p.update(coins=100000,rebirth_count=6)
        if args.equipped:
            p['owned_weapons']['W06']=new_weapon();p['confirmed_loadout']['weapon_slots']=['W01','W17','W03','W06',None]
            p['owned_armors']=['A02'];p['confirmed_loadout']['armor_id']='A02'
            p['owned_turrets']=[dict(instance_id='turret-'+'1'*32,turret_id='T03')]
        repo.save(1,p)
        engine,c=create_game((1280,720),repository=repo,title='糖果防線｜002 原生輸入驗證')
        from ursina import window
        window.title='糖果防線｜002 原生輸入驗證'
        c.record_input=True;original=c.bridge.update;started=time.monotonic();last=0;events=[];routes=[];previous=None;seen=set();samples=[]
        def record():
            nonlocal last,previous
            from ursina import time as engine_time
            real_dt=engine_time.dt;engine_time.dt*=args.time_scale
            try:original()
            finally:engine_time.dt=real_dt
            now=time.monotonic()-started
            if c.state.screen!=previous:routes.append(dict(seconds=round(now,3),screen=c.state.screen));previous=c.state.screen
            b=c.state.battle
            if b:
                for event in b.events:
                    key=(event['attempt_id'],event['sequence'])
                    if key not in seen:events.append(event);seen.add(key)
            if now-last>.3:
                last=now
                state=dict(screen=c.state.screen,slot=c.state.slot,coins=c.state.profile['coins'] if c.state.profile else None,draft=c.state.draft.loadout if c.state.draft else None,battle=b.snapshot() if b else None,projection_height=c.scene.deployment_height)
                samples.append(dict(seconds=round(now,3),screen=c.state.screen,position=b.player.position.tuple() if b else None,aiming=b.player.aiming if b else None,yaw=b.player.yaw if b else None,pitch=b.player.pitch if b else None,deployment_count=len(c.state.draft.loadout['deployments']) if c.state.draft else None,projection_center=list(c.scene.deployment_xy),projection_height=c.scene.deployment_height))
                args.output.write_text(json.dumps(dict(category='實際 Windows 鍵鼠；啟動時隔離資料配置與明列時鐘倍率；不作通關或時序證據',equipped_fixture=args.equipped,time_scale=args.time_scale,seconds=round(now,3),routes=routes,inputs=c.input_log,events=events,samples=samples,state=state,audio_silent=c.audio.silent,audio_error=c.audio.last_error),ensure_ascii=False,indent=2),encoding='utf-8')
        c.bridge.update=record
        try:engine.run()
        finally:c.window_listener.ignoreAll();engine.destroy()

if __name__=='__main__':main()
