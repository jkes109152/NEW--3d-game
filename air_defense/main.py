"""遊戲入口：原生輸入、畫面生命週期、純規則狀態與保存。"""
import argparse
from pathlib import Path
import sys
import time
import traceback
from .config import ROOT, ASSETS, ERRORS, RESOLUTIONS
from .state import AppState, InputFrame
from .weapons import InputCommand
from .save_data import SlotRepository, SaveError
from .ui import Settings, GameUI
from .scene import GameScene
from .audio import AudioBus, generate_sounds


class GameController:
    def __init__(self, engine, repository, settings, silent=False):
        from ursina import Entity
        from direct.showbase.DirectObject import DirectObject
        self.engine=engine
        self.state=AppState(repository)
        self.settings=settings
        self.scene=GameScene(settings)
        self.audio=AudioBus(None if silent else engine.loader)
        self.audio.master=settings.master_volume
        self.audio.effects=settings.effects_volume
        self.ui=GameUI(self)
        self.dialog_slot=None
        self.delete_token=None
        self.return_screen='profile_menu'
        self.fire_requested=False
        self.jump_requested=False
        self.commands=[]; self.command_sequence=0
        self.store_category="weapon"; self.store_filter="all"; self.store_page=0
        self.custom_weapon="W03"; self.custom_tab="upgrade"; self.custom_draft=None
        self.prep_slot=1; self.deploy_selected=None
        self.hud_timer=0.
        self.alert_timer=0.
        self.input_log=[]
        self.record_input=False
        self.focus_checks=True
        self.bridge=Entity()
        self.bridge.update=self.update
        self.bridge.input=self.input
        self.window_listener=DirectObject()
        self.window_listener.accept('window-event',self.window_event)
        self.scene.menu_view()
        self.ui.show()

    def route(self,name):
        if self.state.pending_save and name!="save_error":name="save_error"
        self.state.screen=name
        self.ui.show(name)

    def select_slot(self,slot):
        try:
            self.state.select_slot(slot)
            self.ui.show()
        except SaveError as exc:
            self.dialog_slot=slot
            if exc.code=='corrupt':
                try:
                    self.state.repository.prepare_recovery(slot)
                    self.route('recover_confirm')
                except SaveError as backup_error: self.ui.toast(str(backup_error),5)
            else: self.ui.toast(str(exc))

    def start(self):
        if self.state.begin_preparation():
            self.cleanup_battle();self.ui.show()
            if self.state.draft.messages:
                self.ui.toast('失效部署已撤回庫存：'+ '、'.join(ERRORS.get(reason,reason) for reason in self.state.draft.messages),5)

    def prep_next(self):
        error=self.state.next_preparation()
        if error:self.ui.toast(ERRORS.get(error,error));return
        if self.state.screen=='prepare_deployment':self.scene.deployment_view()
        else:self.scene.end_deployment()
        self.ui.show()

    def confirm_start(self):
        battle=self.state.confirm_and_start(seed=time.time_ns()&0xffffffff)
        if not battle:
            self.ui.show();self.ui.toast(ERRORS.get(self.state.error,self.state.error or '請檢查出戰配置'));return
        self.scene.end_deployment();self.scene.teardown();self.commands=[]
        self.scene.sync(battle,0);self.ui.show('battle');self.ui.update_hud(battle);self.set_mouse_capture(True)

    def prep_armor(self,key):
        error=self.state.set_draft_armor(key)
        if error:self.ui.toast(ERRORS.get(error,error))
        else:self.ui.show()
    def prep_weapon(self,key):
        error=self.state.set_draft_slot(self.prep_slot,key)
        if error:self.ui.toast(ERRORS.get(error,error))
        else:self.ui.show()
    def choose_prep_slot(self,slot):self.prep_slot=slot;self.ui.show()
    def swap_prep_slot(self,delta):
        slots=self.state.draft.loadout['weapon_slots'];other=(self.prep_slot-1+delta)%5;slots[self.prep_slot-1],slots[other]=slots[other],slots[self.prep_slot-1];self.prep_slot=other+1;self.ui.show()
    def store_select(self,category=None,filter=None,page=None):
        if category:self.store_category=category;self.store_page=0
        if filter:self.store_filter=filter;self.store_page=0
        if page is not None:self.store_page=page
        self.route('store')
    def shop_action(self,kind,**fields):
        result=self.state.transaction(kind,**fields)
        if self.state.screen=='weapon_customize' and self.custom_weapon in self.state.profile['owned_weapons']:
            from copy import deepcopy
            owned=self.state.profile['owned_weapons'][self.custom_weapon]
            if self.custom_draft is None:self.custom_draft=deepcopy(owned)
            else:
                for key in ('upgrade_levels','owned_attachments','owned_colors','owned_patterns'):self.custom_draft[key]=deepcopy(owned[key])
        self.ui.show();self.ui.toast(ERRORS.get(result['reason'],result['reason']))
        if result['result_code']=='applied':self.audio.play('shop')
    def customize(self,weapon_id):
        from copy import deepcopy
        self.custom_weapon=weapon_id;self.custom_draft=deepcopy(self.state.profile['owned_weapons'].get(weapon_id));self.custom_tab='upgrade';self.route('weapon_customize')
    def customize_tab(self,tab):self.custom_tab=tab;self.ui.show()
    def custom_select(self,field,key,slot=None):
        if slot:self.custom_draft['selected_attachments'][slot]=key
        else:self.custom_draft[field]=key
        self.ui.show()
    def apply_custom(self):
        d=self.custom_draft;self.shop_action('customize_weapon',weapon_id=self.custom_weapon,selected_attachments=d['selected_attachments'],selected_color=d['selected_color'],selected_pattern=d['selected_pattern'])
    def deploy_select(self,key):self.deploy_selected=key;self.ui.show()
    def deploy_remove(self):
        if self.deploy_selected:self.state.remove_turret(self.deploy_selected);self.scene.sync_deployment(self.state.draft,self.state.profile);self.ui.show()
    def deploy_click(self):
        from ursina import mouse
        if self.ui.blocks_deployment(mouse.position):return
        pos=self.scene.ground_point(mouse.position)
        if pos is None:return
        if not self.deploy_selected:
            nearest=min(self.state.draft.loadout['deployments'],key=lambda t:(t['x']-pos.x)**2+(t['z']-pos.z)**2,default=None)
            if nearest and (nearest['x']-pos.x)**2+(nearest['z']-pos.z)**2<9:self.deploy_select(nearest['instance_id'])
            return
        error=self.state.place_turret(self.deploy_selected,pos.x,pos.z)
        if error:self.ui.toast(ERRORS.get(error,error))
        else:self.ui.show()
    def queue_command(self,kind,value=None):
        self.command_sequence+=1;self.commands.append(InputCommand(self.command_sequence,kind,value))

    def set_mouse_capture(self,captured):
        from ursina import application, mouse
        if application.window_type=='onscreen':
            mouse.locked=captured
            mouse.visible=not captured

    def release_mouse(self):
        from ursina import held_keys
        self.set_mouse_capture(False)
        self.fire_requested=False; self.jump_requested=False;self.commands=[]
        for key in ('w','a','s','d','space','left mouse'): held_keys[key]=0

    def pause(self):
        if self.state.battle and self.state.battle.phase=='active':
            self.state.battle.pause()
            self.release_mouse()
            self.audio.stop()
            self.route('pause')

    def resume(self):
        if not self.state.battle: return
        self.state.battle.resume()
        self.route('battle')
        self.set_mouse_capture(True)

    def window_event(self,window):
        if window and self.focus_checks and not window.getProperties().getForeground(): self.pause()

    def leave_battle(self):
        self.state.leave_battle()
        self.cleanup_battle()
        self.ui.show()

    def show_menu(self):
        if self.state.pending_save: self.route('save_error'); return
        self.state.show_menu()
        self.cleanup_battle()
        self.ui.show()

    def cleanup_battle(self):
        self.release_mouse()
        self.scene.teardown()
        self.audio.stop()
        self.scene.menu_view()

    def return_slots(self):
        if self.state.pending_save: self.route('save_error'); return
        self.state.profile=None; self.state.slot=None
        self.route('slot_select')

    def purchase(self,key):
        result=self.state.purchase(key)
        if self.state.pending_save: self.route('save_error')
        else: self.ui.show('store')
        if result=='applied': self.audio.play('shop')
        self.ui.toast(ERRORS.get(result,result))

    def request_delete(self,slot):
        self.dialog_slot=slot
        self.delete_token=self.state.repository.request_delete(slot)
        self.route('delete_confirm')

    def confirm_delete(self):
        try:
            deleted=self.state.repository.confirm_delete(self.dialog_slot,self.delete_token)
            self.delete_token=None
            self.route('slot_select')
            self.ui.toast('已刪除此欄位' if deleted else '刪除確認已失效，請重新選擇欄位')
        except SaveError as exc:
            self.delete_token=None
            self.route('slot_select')
            self.ui.toast(str(exc))

    def confirm_recover(self):
        try:
            self.state.repository.recover(self.dialog_slot,confirm=True)
            self.select_slot(self.dialog_slot)
            self.ui.toast('原始檔案已備份，新的紀錄已建立')
        except SaveError as exc: self.ui.toast(str(exc),5)

    def request_rebirth(self):
        p=self.state.profile
        if not p['rebirth_available']: self.ui.toast(ERRORS['rebirth_unavailable']); return
        if p['coins']<1000*(p['rebirth_count']+1): self.ui.toast(ERRORS['insufficient_coins']); return
        self.route('rebirth_confirm')

    def confirm_rebirth(self):
        result=self.state.rebirth()
        self.route('save_error' if self.state.pending_save else 'profile_menu')
        self.ui.toast('重生完成，重新配發三把基礎武器' if result=='applied' else ERRORS.get(result,result))

    def retry_save(self):
        if self.state.retry_save():
            self.ui.show()
            self.ui.toast('保存完成')
        else: self.ui.toast('保存仍未完成，請檢查資料夾後重試',4)

    def open_settings(self):
        self.return_screen=self.state.screen
        self.route('settings')

    def change_setting(self,key,delta):
        settings=self.settings
        options={'quality':['low','medium','high'],'resolution':list(RESOLUTIONS),'aim_mode':['modern','legacy']}
        if key in options:
            choices=options[key]
            setattr(settings,key,choices[(choices.index(getattr(settings,key))+delta)%len(choices)])
        elif key in ('fullscreen','reduced_motion'): setattr(settings,key,not getattr(settings,key))
        else:
            low,high=(.2,3) if key=='sensitivity' else (0,1)
            setattr(settings,key,round(max(low,min(high,getattr(settings,key)+delta*.1)),1))
        self.apply_settings()
        try: settings.save(self.state.repository.root)
        except OSError: self.ui.toast('設定尚未保存，請檢查寫入權限')
        self.ui.show('settings')

    def apply_settings(self):
        from ursina import application, window
        self.audio.master=self.settings.master_volume
        self.audio.effects=self.settings.effects_volume
        if application.window_type=='onscreen':
            if window.fullscreen!=self.settings.fullscreen: window.fullscreen=self.settings.fullscreen
            if not self.settings.fullscreen and tuple(window.size)!=self.settings.resolution:
                window.size=self.settings.resolution
        self.scene.apply_quality(self.settings.quality)

    def back(self):
        screen=self.state.screen
        if screen=='battle': self.pause()
        elif screen=='pause': self.resume()
        elif screen=='settings': self.route(self.return_screen)
        elif screen in ('delete_confirm','recover_confirm'):
            if self.delete_token: self.state.repository.cancel_delete(self.delete_token); self.delete_token=None
            self.route('slot_select')
        elif screen.startswith('prepare_'):
            self.state.back_preparation()
            if self.state.screen=='prepare_deployment':self.scene.deployment_view()
            else:self.scene.end_deployment()
            self.ui.show()
        elif screen=='weapon_customize':self.custom_draft=None;self.route('store')
        elif screen=='profile_menu': self.return_slots()
        elif screen=='slot_select': self.quit()
        elif screen=='save_error': self.ui.toast('請先完成保存')
        elif screen.startswith('result_'): self.show_menu()
        else: self.route('profile_menu')

    def input(self,key):
        if self.record_input:self.input_log.append(dict(key=key,screen=self.state.screen,source='engine_input'))
        battle=self.state.battle
        if key=='left mouse up':
            if battle:battle.require_release=False;battle.held=False
            if self.state.screen=='battle':self.queue_command('fire_up')
        if key=='escape':self.back();return
        if self.state.screen=='prepare_deployment':
            if key=='left mouse down':self.deploy_click()
            elif key=='scroll up':self.scene.deployment_zoom(.9)
            elif key=='scroll down':self.scene.deployment_zoom(1/.9)
            elif key=='delete':self.deploy_remove()
            elif key=='right mouse down':self.deploy_selected=None;self.ui.show()
            else:self.ui.input(key)
            return
        if self.state.screen=='battle' and battle and battle.phase=='active':
            if len(key)==1 and key in '12345':self.queue_command('select_slot',int(key))
            elif key=='right mouse down':self.queue_command('toggle_aim')
            elif key=='left mouse down':self.queue_command('fire_down')
            elif key=='r':self.queue_command('reload')
            elif key=='space':self.queue_command('jump')
        elif key=='space' and self.state.screen=='profile_menu':self.start()
        else:self.ui.input(key)

    def update(self):
        from ursina import time as engine_time, mouse, held_keys
        dt=engine_time.dt
        self.ui.tick(dt); self.audio.tick()
        battle=self.state.battle
        if self.state.screen=='prepare_deployment':
            self.scene.deployment_pan((held_keys['d']-held_keys['a'])*dt,(held_keys['w']-held_keys['s'])*dt)
            self.scene.deployment_drag(mouse.position,bool(held_keys['middle mouse']))
            blocked=self.ui.blocks_deployment(mouse.position)
            self.scene.deployment_ghost(self.state.draft,self.deploy_selected,None if blocked else self.scene.ground_point(mouse.position))
        if not battle or self.state.screen!='battle' or battle.phase!='active': return
        look=(mouse.velocity.x*100*self.settings.sensitivity,-mouse.velocity.y*100*self.settings.sensitivity)
        frame=InputFrame(move_x=held_keys['d']-held_keys['a'],move_z=held_keys['w']-held_keys['s'],look_delta=look,
                         jump_pressed=self.jump_requested,fire_pressed=self.fire_requested,commands=tuple(self.commands))
        self.commands=[]
        self.fire_requested=False; self.jump_requested=False
        snapshot=battle.advance(dt,frame)
        self.scene.sync(battle,dt,snapshot['events'])
        self.audio.consume(snapshot['events'])
        self.hud_timer+=dt; self.alert_timer=max(0,self.alert_timer-dt)
        if self.hud_timer>=.05:
            self.hud_timer=0
            self.ui.update_hud(battle)
        for event in snapshot['events']:
            if event['kind']=='error': self.ui.toast(ERRORS.get(event['code'],'暫時無法發射'))
        if any(a.hp>0 and a.remaining<=8 for a in battle.aircraft.values()) and self.alert_timer<=0:
            self.audio.play('alert'); self.alert_timer=2
        if battle.phase in ('success','failure'):
            self.state.settle()
            self.release_mouse()
            self.ui.show('save_error' if self.state.pending_save else self.state.screen)

    def metrics(self):
        from ursina import scene
        return {**self.scene.metrics(),'engine_entities':len(scene.entities),'engine_tasks':len(self.engine.taskMgr.getTasks()),
                'input_handlers':1,'lock_markers':len(self.ui.markers),
                'active_missiles':len(self.state.battle.missiles) if self.state.battle else 0,
                'active_rockets':len(self.state.battle.rockets) if self.state.battle else 0,
                'pending_commands':len(self.commands),'core_tracers':len(self.scene.core_tracers),
                'ui_layers':int(self.ui.layer is not None),'ui_buttons':len(self.ui.buttons)}

    def quit(self):
        if self.state.pending_save: self.route('save_error'); return
        self.audio.stop()
        self.engine.userExit()


def install_keyboard_adapter(engine):
    """統一 Windows 邏輯鍵事件，讓實體、輔助輸入及不同鍵盤配置只送一次。

    Ursina 8.3 只接受英數 raw 掃描碼，會丟棄 Windows 合成的 buttonDown。
    沿用引擎的命名與 held_keys 管理，但解除重複的 raw 訂閱。
    """
    from ursina.main import keyboard_keys
    for key in keyboard_keys:
        for suffix in ('','-up','-repeat'):engine.ignore(f'raw-{key}{suffix}')
    def normalized(key):
        if 'mouse' not in key:
            for prefix in ('control-','shift-','alt-'):key=key.replace(prefix,'')
        return key
    def down(key):
        from ursina import mouse
        if 'mouse' in key and not mouse.locked:mouse.update()
        engine.input(normalized(key),True)
    engine.accept('buttonDown',down)
    engine.accept('buttonUp',lambda key:engine.input_up(normalized(key),True))
    engine.accept('buttonHold',lambda key:engine.input_hold(normalized(key),True))


def create_game(size=None, offscreen=False, repository=None, silent=False, title='糖果防線｜3D 防空守衛'):
    from panda3d.core import loadPrcFileData
    repo=repository or SlotRepository()
    settings=Settings.load(repo.root)
    if size: settings.resolution=tuple(size); settings.fullscreen=False
    loadPrcFileData('', 'notify-level warning\ntextures-power-2 up\nframebuffer-multisample 0\nmultisamples 0\nthreading-model Cull/Draw\n')
    if silent: loadPrcFileData('', 'audio-library-name null')
    from ursina import Ursina, application
    application.asset_folder=ASSETS
    application.fonts_folder=ASSETS/'fonts'
    generate_sounds()
    engine=Ursina(title=title,size=settings.resolution,fullscreen=settings.fullscreen,
                  development_mode=False,editor_ui_enabled=False,borderless=False,vsync=False,
                  window_type='offscreen' if offscreen else 'onscreen')
    # Ursina 8.3 的 apply_settings 會把傳入的 vsync=False 覆回 True。
    # 在首次繪製前直接設定 Panda3D；不修改第三方套件。
    loadPrcFileData('', 'sync-video false')
    # 以有上限的繪製時鐘節流，避免驅動垂直同步把短幀阻塞成多個刷新週期。
    from panda3d.core import ClockObject
    render_clock=ClockObject.getGlobalClock();render_clock.setMode(ClockObject.MLimited);render_clock.setFrameRate(120)
    install_keyboard_adapter(engine)
    if offscreen:
        from ursina import camera
        # 離屏緩衝區沒有視窗尺寸變更事件，需主動初始化相同的 UI 投影。
        camera.ui_lens.setFilmSize(camera._ui_size*.5*engine.getAspectRatio(),camera._ui_size*.5)
    controller=GameController(engine,repo,settings,silent=silent)
    return engine,controller


def main(argv=None):
    parser=argparse.ArgumentParser(description='3D 防空守衛')
    parser.add_argument('--size',choices=('1280x720','1920x1080'))
    parser.add_argument('--offscreen',action='store_true')
    parser.add_argument('--silent',action='store_true')
    parser.add_argument('--smoke-seconds',type=float,default=0)
    parser.add_argument('--screenshot',type=Path)
    args=parser.parse_args(argv)
    try:
        size=tuple(map(int,args.size.split('x'))) if args.size else None
        engine,controller=create_game(size,args.offscreen,silent=args.silent)
        if args.smoke_seconds:
            from panda3d.core import Filename
            deadline=time.perf_counter()+args.smoke_seconds
            while time.perf_counter()<deadline: engine.step()
            if args.screenshot:
                args.screenshot.parent.mkdir(parents=True,exist_ok=True)
                engine.win.saveScreenshot(Filename.fromOsSpecific(str(args.screenshot.resolve())))
            controller.window_listener.ignoreAll()
            engine.destroy()
        else: engine.run()
        return 0
    except Exception:
        path=ROOT/'artifacts'/'game-error.log'
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(traceback.format_exc(),encoding='utf-8')
        print('遊戲啟動失敗；詳細原因：'+str(path),file=sys.stderr)
        traceback.print_exc()
        return 5

if __name__=='__main__': raise SystemExit(main())
