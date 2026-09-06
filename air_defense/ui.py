"""繁中畫面路由、設定與輸入焦點；圖形匯入延後至建立介面。"""
from dataclasses import dataclass, asdict
from pathlib import Path
import json
from .save_data import atomic_json
from .config import ASSETS, RESOLUTIONS, WEAPONS, WEAPON_NAMES, ERRORS
from .progression import UPGRADES, upgrade_level, caps, price, purchase_error, lock_time

INK='#10262d'
PANEL='#19353d'
MUTED='#a1b9b9'
WHITE='#e8eee2'
ACCENT='#d8bb7d'
TEAL='#91c6b4'
RED='#e78b78'

@dataclass
class Settings:
    sensitivity: float = 1.0
    master_volume: float = .7
    effects_volume: float = .8
    quality: str = 'medium'
    fullscreen: bool = False
    reduced_motion: bool = False
    resolution: tuple = (1280,720)
    aim_mode: str = 'modern'

    @classmethod
    def load(cls, root):
        settings=cls()
        try:
            data=json.loads((Path(root)/'settings.json').read_text(encoding='utf-8'))
            if not isinstance(data,dict): return settings
            for key,(low,high) in {'sensitivity':(.2,3),'master_volume':(0,1),'effects_volume':(0,1)}.items():
                value=data.get(key)
                if type(value) in (int,float) and low<=value<=high: setattr(settings,key,value)
            for key in ('fullscreen','reduced_motion'):
                if type(data.get(key)) is bool: setattr(settings,key,data[key])
            if data.get('quality') in ('low','medium','high'): settings.quality=data['quality']
            if data.get('resolution') in [list(r) for r in RESOLUTIONS]: settings.resolution=tuple(data['resolution'])
        except (OSError,ValueError,UnicodeError): pass
        return settings

    def save(self, root):
        data=asdict(self)
        data.pop('aim_mode')
        atomic_json(Path(root)/'settings.json',data)

def reticle_kind(slot, aiming):
    if aiming and slot in (1,5): return 'lock'
    if aiming and slot==2: return 'scope'
    return 'crosshair'

def shop_key(key):
    from .progression import UPGRADES
    if key not in '1234567890' or len(key)!=1: return None
    return UPGRADES['1234567890'.index(key)][0]

class GameUI:
    def __init__(self, controller):
        from ursina import Entity, Text, camera
        self.controller=controller
        self.root=Entity(parent=camera.ui)
        self.layer=None
        self.focus=0
        self.buttons=[]
        self.route=None
        self.generation=0
        self.hud={}
        self.markers={}
        self.toast_time=0
        self.last_toast=None
        Text.default_font='NotoSansCJKtc-Regular.otf'
        Text.default_resolution=64
        self.toast_label=Text(parent=self.root,text='',y=-.345,z=-30,origin=(0,0),scale=.85,color=self.tint(ACCENT))
        self.toast_back=self.rect(0,-.345,.64,.046,INK,parent=self.root,z=-29,alpha=.95)
        self.toast_back.enabled=False

    @staticmethod
    def tint(hex_color):
        from ursina import color
        return color.hex(hex_color)

    def rect(self,x,y,w,h,tint=PANEL,parent=None,z=0,alpha=1):
        from ursina import Entity
        return Entity(parent=parent or self.layer,model='quad',position=(x,y,z),scale=(w,h),
                      color=self.tint(tint),alpha=alpha,add_to_scene_entities=False)

    def text(self, value,x,y,size=1,tint=WHITE,parent=None,center=False,**kwargs):
        from ursina import Text
        return Text(parent=parent or self.layer,text=value,position=(x,y,-2),scale=size,
                    origin=(0,.5) if center else (-.5,.5),color=self.tint(tint),**kwargs)

    def button(self,label,x,y,w,h,action,primary=False,size=.95,focusable=True):
        from ursina import Button
        generation=self.generation
        button=Button(parent=self.layer,text='',position=(x,y,-1),scale=(w,h),
                      color=self.tint(ACCENT if primary else PANEL),highlight_color=self.tint('#688980'),
                      pressed_color=self.tint(TEAL),radius=0)
        # 舊畫面的延遲點擊永遠不能提交至新畫面。
        button.on_click=lambda: action() if generation==self.generation else None
        self.text(label,x,y+h*.20,size,INK if primary else WHITE,center=True)
        button.base_tint=ACCENT if primary else PANEL
        if focusable: self.buttons.append(button)
        return button

    def heading(self,kicker,title,subtitle=''):
        self.rect(0,0,1.78,1,INK,alpha=.96)
        self.rect(-.786,.407,.008,.054,ACCENT)
        self.text(kicker,-.756,.433,.72,ACCENT)
        self.text(title,-.76,.365,1.9)
        if subtitle: self.text(subtitle,-.756,.296,.78,MUTED)
        self.rect(0,.264,1.52,.002,'#44616a')
        self.text('3D 防空守衛  /  城市防禦指揮部',-.76,-.444,.68,MUTED)
        self.text('↑ ↓ 選擇    Enter 確認    Esc 返回',.25,-.444,.68,MUTED)

    def show(self,route=None):
        app=self.controller.state
        self.route=route or app.screen
        self.clear()
        self.hud={}; self.markers={}
        getattr(self,'show_'+self.route,self.show_profile_menu)()
        self.focus_button(0)

    def focus_button(self,index):
        if not self.buttons: return
        self.focus=index%len(self.buttons)
        for i,button in enumerate(self.buttons):
            button.color=self.tint('#557970' if i==self.focus else button.base_tint)

    def input(self,key):
        if key in ('down arrow','tab'): self.focus_button(self.focus+1)
        elif key=='up arrow': self.focus_button(self.focus-1)
        elif key=='enter' and self.buttons: self.buttons[self.focus].on_click()
        elif self.route=='store' and shop_key(key): self.controller.purchase(shop_key(key))
        elif self.route=='slot_select' and key in '12345' and len(key)==1: self.controller.select_slot(int(key))

    def toast(self,message,duration=2.5):
        self.toast_label.text=message
        self.toast_back.enabled=True
        self.toast_time=duration
        self.last_toast=message

    def tick(self,dt):
        if self.toast_time>0:
            self.toast_time=max(0,self.toast_time-dt)
            if self.toast_time==0:
                self.toast_label.text=''
                self.toast_back.enabled=False

    def show_slot_select(self):
        self.heading('防守者登錄  /  01','選擇你的防守紀錄','五個獨立欄位。選擇空欄位，即可建立新的戰役。')
        for index,(slot,profile,error) in enumerate(self.controller.state.repository.list_slots()):
            y=.199-index*.105
            subtitle='尚未建立  ·  從第一道防線開始'
            if profile:
                subtitle=f"金幣 {profile['coins']:,} 元     重生 {profile['rebirth_count']} 次     飛機上限 {profile['max_aircraft_count']} 架"
            if error: subtitle='資料無法讀取  ·  選擇後可備份並重建'
            self.button('',-.077,y,1.366,.085,lambda s=slot:self.controller.select_slot(s))
            self.text(f'0{slot}',-.72,y+.023,1.16,ACCENT)
            self.text(f'防守紀錄 {slot}',-.60,y+.03,.89)
            self.text(subtitle,-.32,y+.018,.78,RED if error else MUTED)
            if profile or error:
                self.button('刪除',.694,y,.13,.085,lambda s=slot:self.controller.request_delete(s),size=.75)
        self.button('設定',-.62,-.36,.28,.05,self.controller.open_settings,size=.8)
        self.button('離開',-.30,-.36,.28,.05,self.controller.quit,size=.8)

    def show_profile_menu(self):
        app=self.controller.state; profile=app.profile
        self.rect(-.455,0,.87,1,INK,alpha=.96)
        self.text('城市防禦指揮部',-.76,.407,.85,ACCENT)
        self.text('3D 防空守衛',-.76,.321,2.25)
        self.text('守住天空。守住回家的路。',-.757,.23,.90,MUTED)
        self.rect(-.471,.176,.576,.002,'#52706e')
        self.text(f"紀錄 0{app.slot}     金幣 {profile['coins']:,} 元",-.756,.136,.9)
        self.text(f"重生 {profile['rebirth_count']} 次    /    敵機上限 {profile['max_aircraft_count']} 架",-.756,.086,.78,MUTED)
        self.button(f'開始防守    {app.cursor[0]}-{app.cursor[1]}',-.472,-.016,.575,.075,self.controller.start,primary=True,size=1.04)
        self.button('裝備整備  /  商店',-.472,-.111,.575,.065,lambda:self.controller.route('store'))
        self.button('自願重生',-.622,-.197,.275,.061,self.controller.request_rebirth,size=.85)
        self.button('設定',-.322,-.197,.275,.061,self.controller.open_settings,size=.85)
        self.button('返回選檔',-.622,-.282,.275,.061,self.controller.return_slots,size=.85)
        self.button('離開遊戲',-.322,-.282,.275,.061,self.controller.quit,size=.85)
        self.text('移動 WASD    跳躍 Space    切槍 1–5',-.756,-.381,.67,MUTED)
        self.text('左鍵射擊    右鍵切換瞄準    Esc 暫停',-.756,-.419,.67,MUTED)
        self.rect(.47,-.318,.60,.20,INK,alpha=.88)
        self.text('防禦目標  /  中央指揮大樓',.205,-.242,.9,ACCENT)
        self.text('擊落全部飛機，再清除下降與地面敵兵。\n每關結算後由你決定何時再次出擊。',.205,-.288,.77,MUTED)

    def show_store(self):
        p=self.controller.state.profile
        self.heading(f"裝備整備  /  金幣 {p['coins']:,} 元",'升級你的防線','滑鼠或快捷鍵購買。升級永久保留，每次出擊套用最新配置。')
        for index,(key,name,base,description) in enumerate(UPGRADES):
            y=.219-index*.06; level=upgrade_level(p,key); cap=caps(p['rebirth_count']).get(key,1)
            digit='1234567890'[index]
            cost=price(p,key); error=purchase_error(p,key)
            self.button('',0,y,1.52,.053,lambda k=key:self.controller.purchase(k),size=.8)
            self.text(f'{digit}   {name}（{level}/{cap}）',-.73,y+.022,.78,WHITE if not error else MUTED)
            self.text(f'{cost:,} 元',.36,y+.022,.78,ACCENT)
            status='可購買' if not error else ERRORS.get(error,error)
            self.text(status,.59,y+.021,.65,TEAL if not error else MUTED)
            next_value=min(level+1,cap)
            details=self.upgrade_details(key,level,next_value)
            self.text(description+'  ·  '+details,-.678,y-.004,.58,MUTED)
        self.button('返回主選單',0,-.403,.34,.052,self.controller.back,primary=True,size=.85)

    @staticmethod
    def upgrade_details(key,level,next_level):
        formulas={'max_hp':lambda n:f'{100+10*n} HP','armor':lambda n:f'減傷 {n}',
                  'aa_lock_time':lambda n:f'{max(.1,3-.15*n):.2f} 秒',
                  'aa_whitebox':lambda n:f'{1+.1*n:.1f} 倍','weapon_cooldown':lambda n:f'{max(.5,1-.05*n)*100:.0f}%',
                  'auto_defense_capacity':lambda n:f'{1+n} 台'}
        f=formulas.get(key,lambda n:'已解鎖' if n else '未解鎖')
        return f'目前 {f(level)} → 下級 {f(next_level)}'

    def show_settings(self):
        settings=self.controller.settings
        self.heading('偏好設定','調整你的操作','瞄準模式保留至本次程式結束，其餘設定自動保存。')
        rows=[('sensitivity','滑鼠靈敏度',f'{settings.sensitivity:.1f}'),
              ('master_volume','主音量',f'{settings.master_volume:.0%}'),
              ('effects_volume','音效音量',f'{settings.effects_volume:.0%}'),
              ('quality','畫質',{'low':'低','medium':'中','high':'高'}[settings.quality]),
              ('resolution','解析度',f'{settings.resolution[0]} × {settings.resolution[1]}'),
              ('fullscreen','全螢幕','開啟' if settings.fullscreen else '關閉'),
              ('reduced_motion','降低動態效果','開啟' if settings.reduced_motion else '關閉'),
              ('aim_mode','防空瞄準模式','新版' if settings.aim_mode=='modern' else '舊版')]
        for i,(key,label,value) in enumerate(rows):
            y=.203-i*.065
            self.rect(0,y,1.30,.057,PANEL)
            self.text(label,-.615,y+.016,.85)
            self.text(value,.03,y+.016,.85,ACCENT)
            self.button('－',.39,y,.10,.045,lambda k=key:self.controller.change_setting(k,-1),size=.8)
            self.button('＋',.53,y,.10,.045,lambda k=key:self.controller.change_setting(k,1),size=.8)
        self.button('套用並返回',0,-.373,.36,.062,self.controller.back,primary=True)

    def show_pause(self):
        self.heading('任務暫停','防守已暫停','時間、敵人、冷卻與回血均已停止。返回後從此刻繼續。')
        self.button('繼續防守',0,.14,.55,.079,self.controller.resume,primary=True)
        self.button('設定',0,.035,.55,.068,self.controller.open_settings)
        self.button('結束本局，返回主選單',0,-.065,.55,.068,self.controller.leave_battle,size=.89)
        self.text('主動結束不發放獎勵；下一次從 1-1 開始。',0,-.166,.8,MUTED,center=True)

    def show_delete_confirm(self):
        self.heading('刪除確認',f'刪除防守紀錄 {self.controller.dialog_slot}？','此欄位的正式紀錄與所屬損壞備份將被刪除。')
        self.text('其他四個欄位不受影響。',0,.13,1,MUTED,center=True)
        self.button('取消，保留紀錄',-.24,-.06,.43,.075,self.controller.back,primary=True,size=.9)
        self.button('確認刪除此欄位',.24,-.06,.43,.075,self.controller.confirm_delete,size=.9)

    def show_recover_confirm(self):
        self.heading('紀錄復原',f'紀錄 {self.controller.dialog_slot} 無法載入','原始檔案與位元組備份均已保留。確認後建立空白紀錄。')
        self.text('你也可以取消，稍後手動檢查存檔。\n重建前會再次確認原始檔案備份完整。',0,.13,.92,MUTED,center=True)
        self.button('取消',-.24,-.06,.43,.075,self.controller.back,primary=True)
        self.button('備份並重建',.24,-.06,.43,.075,self.controller.confirm_recover)

    def show_rebirth_confirm(self):
        p=self.controller.state.profile; cost=1000*(p['rebirth_count']+1)
        self.heading('自願重生','再一次，守住更大的天空',f"本次所需 {cost:,} 元  /  目前持有 {p['coins']:,} 元")
        self.text(f"確認後，全部金幣歸零。\n重生次數增為 {p['rebirth_count']+1}，敵機上限增為 {p['max_aircraft_count']+1}。\n永久升級與武器保留，從 1-1 重新出發。",0,.14,1,WHITE,center=True)
        self.button('取消',-.24,-.12,.43,.075,self.controller.back,primary=True)
        self.button('確認重生',.24,-.12,.43,.075,self.controller.confirm_rebirth)

    def show_save_error(self):
        self.heading('保存尚未完成','進度仍保留在記憶體','請重試保存。完成前無法購買、切換紀錄或開始新一局。')
        self.text('已套用的交易不會再次扣款或重複發放獎勵。',0,.14,.95,MUTED,center=True)
        self.button('重試保存',0,-.02,.5,.078,self.controller.retry_save,primary=True)
        self.text('可先檢查存檔資料夾是否有寫入權限或足夠空間。',0,-.15,.8,MUTED,center=True)

    def show_result_success(self): self.show_result(True)
    def show_result_failure(self): self.show_result(False)

    def show_result(self,success):
        app=self.controller.state; result=app.last_result
        self.heading(f"防守報告  /  {result['level']}",'防線守住了' if success else '防線遭到突破',
                     '所有敵機與敵兵已清除。' if success else ERRORS.get(result['reason'],'本局結束'))
        self.text(f"+ {result['reward']:,} 元" if success else '本局獎勵  0 元',0,.17,2.1,ACCENT,center=True)
        self.text(f"目前金幣 {app.profile['coins']:,} 元    下一次出擊 {app.cursor[0]}-{app.cursor[1]}",0,.058,.92,MUTED,center=True)
        self.button('返回主選單',0,-.11,.53,.082,self.controller.show_menu,primary=True)
        if app.profile['rebirth_available']: self.text('已取得自願重生資格，可於主選單查看。',0,-.232,.82,TEAL,center=True)

    def show_battle(self):
        from ursina import Entity
        self.rect(-.622,.389,.44,.146,INK,alpha=.90)
        self.rect(.622,.389,.44,.146,INK,alpha=.90)
        self.rect(0,.411,.59,.10,INK,alpha=.88)
        self.hud['player']=self.text('',-.82,.446,.88)
        self.hud['health']=self.rect(-.809,.39,.37,.009,TEAL)
        self.hud['health'].origin_x=-.5
        self.hud['regen']=self.text('',-.82,.357,.62,MUTED)
        self.hud['city']=self.text('',.42,.446,.88)
        self.hud['citybar']=self.rect(.425,.39,.37,.009,ACCENT)
        self.hud['citybar'].origin_x=-.5
        self.hud['threat']=self.text('',.42,.357,.62,MUTED)
        self.hud['stage']=self.text('',0,.445,.95,ACCENT,center=True)
        self.hud['counts']=self.text('',0,.408,.61,MUTED,center=True)
        self.hud['alert']=self.text('',0,.317,.8,RED,center=True)
        self.hud['economy']=self.text('',-.82,-.348,.70,MUTED)
        self.hud['hint']=self.text('右鍵切換瞄準  /  左鍵射擊',.35,-.348,.65,MUTED)
        self.rect(-.615,-.363,.46,.041,INK,alpha=.94)
        self.rect(.612,-.363,.46,.041,INK,alpha=.94)
        for slot in range(1,6):
            x=-.632+(slot-1)*.316
            panel=self.rect(x,-.414,.303,.075,INK,alpha=.94)
            self.hud['slot'+str(slot)]=panel
            self.hud['name'+str(slot)]=self.text(f'{slot}  {WEAPON_NAMES[slot-1]}',x-.139,-.387,.66)
            self.hud['cd'+str(slot)]=self.text('',x-.139,-.422,.62,MUTED)
        self.cross=Entity(parent=self.layer,add_to_scene_entities=False)
        for x,y,w,h in ((-.013,0,.012,.002),(.013,0,.012,.002),(0,-.013,.002,.012),(0,.013,.002,.012)):
            self.rect(x,y,w,h,WHITE,parent=self.cross)
        self.lock_root=Entity(parent=self.layer,add_to_scene_entities=False)
        self.lock_lines=[self.rect(0,0,1,1,WHITE,parent=self.lock_root) for _ in range(4)]
        self.hud['locklabel']=self.text('',0,-.147,.72,WHITE,parent=self.lock_root,center=True)
        self.hud['lockback']=self.rect(0,-.147,.36,.036,INK,parent=self.lock_root,alpha=.92)
        self.hud['lockbar']=self.rect(-.1,-.18,.2,.003,TEAL,parent=self.lock_root)
        self.hud['lockbar'].origin_x=-.5
        self.scope=Entity(parent=self.layer,add_to_scene_entities=False)
        for x,y,w,h in ((-.61,0,.56,1),(.61,0,.56,1),(0,.43,.66,.14),(0,-.43,.66,.14)):
            self.rect(x,y,w,h,INK,parent=self.scope,alpha=.98)
        self.rect(0,0,.68,.001,INK,parent=self.scope)
        self.rect(0,0,.001,.68,INK,parent=self.scope)
        self.text('狙擊  /  180 m',0,-.312,.65,TEAL,parent=self.scope,center=True)
        self.lock_root.enabled=False; self.scope.enabled=False

    def set_text(self,key,value):
        node=self.hud[key]
        if node.text!=value: node.text=value

    def update_hud(self,battle):
        from ursina import destroy
        from math import tan, radians
        from .entities import direction, V3
        p=battle.player
        self.set_text('player',f'防守者  {p.hp:.0f} / {p.max_hp:.0f}')
        self.hud['health'].scale_x=.37*p.hp/p.max_hp
        self.set_text('regen',f'鎧甲 {p.armor}  ·  回血預算 {max(0,p.max_hp*.2-p.healed):.0f}  ·  '+('恢復中' if p.since_damage>=5 and p.hp<p.max_hp else '掩護待命'))
        self.set_text('city',f'城市防線  {battle.city.hp:.0f} / 100')
        self.hud['citybar'].scale_x=.37*battle.city.hp/100
        air=[a for a in battle.aircraft.values() if a.hp>0]
        down=sum(e.phase=='descending' and e.hp>0 for e in battle.enemies.values())
        ground=sum(e.phase=='ground' and e.hp>0 for e in battle.enemies.values())
        self.set_text('stage',f'防守 {battle.level.level_id}    /    {battle.level.A} 架上限')
        self.set_text('counts',f'空中 {len(air)}    下降 {down}    地面 {ground}')
        at_city=any(e.phase=='ground' and (e.position-battle.city.position).horizontal().length()<=10 for e in battle.enemies.values())
        self.set_text('threat','城市遭到攻擊！' if at_city else '守住中央大樓  ·  防禦半徑 10 m')
        seconds=min((a.remaining for a in air),default=99)
        self.set_text('alert',f'空襲警報  /  預估 {seconds:.1f} 秒後突破' if seconds<=8 else '')
        self.set_text('economy',f"金幣 {battle.profile['coins']:,} 元    重生 {battle.profile['rebirth_count']} 次")
        for slot in range(1,6):
            unlocked=WEAPONS[slot-1] in battle.profile['unlocked_weapons']
            self.hud['slot'+str(slot)].color=self.tint('#3e635b' if slot==p.weapon_slot else INK)
            value='未解鎖' if not unlocked else f'冷卻 {p.cooldowns[slot]:.1f} 秒' if p.cooldowns[slot]>.001 else '就緒'
            if slot==4 and unlocked: value+=f'  ·  {p.rpg_ammo}/3 發'
            self.set_text('cd'+str(slot),value)
        kind=reticle_kind(p.weapon_slot,p.aiming)
        self.cross.enabled=kind=='crosshair'; self.scope.enabled=kind=='scope'; self.lock_root.enabled=kind=='lock'
        if kind=='lock':
            size=.21*(1+.1*upgrade_level(battle.profile,'aa_whitebox'))*(2 if p.weapon_slot==5 else 1)
            for node,(x,y,w,h) in zip(self.lock_lines,((0,size/2,size,.0015),(0,-size/2,size,.0015),(-size/2,0,.0015,size),(size/2,0,.0015,size))):
                node.position=(x,y,0); node.scale=(w,h)
            ready=battle.lock.ready(); progress=min((battle.lock.progress[k] for k in battle.lock.valid),default=0)
            wording='鎖定完成 · 左鍵發射' if ready else f'鎖定中 {progress:.0%}' if battle.lock.valid else '搜尋目標'
            self.hud['locklabel'].y=-size/2-.025; self.hud['lockbar'].y=-size/2-.058
            self.hud['lockback'].y=-size/2-.033
            self.hud['lockbar'].scale_x=.2*progress
            self.set_text('locklabel',wording+f'  /  {len(battle.lock.valid)}')
            self.hud['locklabel'].color=self.tint(TEAL if ready else RED if battle.lock.valid else WHITE)
        targets=battle.lock.valid if kind=='lock' else ()
        for key in list(self.markers):
            if key not in targets:
                from .scene import destroy_tree
                destroy_tree(self.markers.pop(key))
        right=direction(p.yaw+90,0); forward=p.forward
        up=V3(forward.y*right.z-forward.z*right.y,forward.z*right.x-forward.x*right.z,forward.x*right.y-forward.y*right.x)
        for key in targets:
            aircraft=battle.aircraft.get(key)
            if not aircraft: continue
            if key not in self.markers:
                from ursina import Entity
                marker=Entity(parent=self.layer,add_to_scene_entities=False)
                marker.label=self.text('',0,.042,.65,RED,parent=marker,center=True)
                marker.lines=[self.rect(0,0,1,1,RED,parent=marker) for _ in range(4)]
                self.markers[key]=marker
            delta=aircraft.position-p.eye; depth=delta.dot(forward)
            if depth<=0: continue
            scale=battle.aspect/(2*tan(radians(battle.fov/2))*depth)
            node=self.markers[key]; node.position=(delta.dot(right)*scale,delta.dot(up)*scale,-3)
            value=battle.lock.progress.get(key,0)
            complete=value>=1-1e-9
            modern=self.controller.settings.aim_mode=='modern'
            label=f'{value:.0%}' if modern else ('完成' if complete else '追蹤')
            if node.label.text!=label: node.label.text=label
            tint=self.tint(TEAL if complete else RED); node.label.color=tint
            parts=((0,.019,.05,.0018),(0,-.019,.05,.0018),(-.025,0,.0018,.038),(.025,0,.0018,.038)) if modern else \
                  ((-.018,0,.014,.002),(.018,0,.014,.002),(0,-.018,.002,.014),(0,.018,.002,.014))
            for line,(x,y,w,h) in zip(node.lines,parts):
                line.position=(x,y,0); line.scale=(w,h); line.color=tint

    def clear(self):
        from ursina import Entity, destroy
        from .scene import destroy_tree
        self.generation+=1
        if self.layer: destroy_tree(self.layer)
        self.layer=Entity(parent=self.root)
        self.buttons=[]
        self.focus=0

    def destroy(self):
        from .scene import destroy_tree
        destroy_tree(self.root)
