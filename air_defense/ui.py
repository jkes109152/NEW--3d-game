"""繁中畫面路由、設定與輸入焦點；圖形匯入延後至建立介面。"""
from dataclasses import dataclass, asdict
from pathlib import Path
import json
from .save_data import atomic_json
from .config import ASSETS, RESOLUTIONS, ERRORS
from .catalog import WEAPONS as ITEMS, ARMORS, TURRETS, CATEGORY_NAMES, MODE_NAMES, ATTACHMENTS, UPGRADE_NAMES, UPGRADE_PRICES, COLORS, PATTERNS, applicable_upgrade, upgrade_cap
from .loadout import resolve_weapon_stats, resolve_player_stats

INK='#edf5fc'
PANEL='#d8e8f2'
MUTED='#526a86'
WHITE='#233656'
ACCENT='#a34776'
TEAL='#267565'
RED='#a43355'

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

def shop_key(key):return None

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
        self.toast_label=Text(parent=self.root,text='',y=-.478,z=-30,origin=(0,0),scale=.70,color=self.tint(ACCENT))
        self.toast_back=self.rect(0,-.478,1.4,.036,INK,parent=self.root,z=-29,alpha=.97)
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
        kwargs.setdefault('line_height',1.4)
        return Text(parent=parent or self.layer,text=value,position=(x,y,-2),scale=size,
                    origin=(0,.5) if center else (-.5,.5),color=self.tint(tint),**kwargs)

    def button(self,label,x,y,w,h,action,primary=False,size=.95,focusable=True):
        from ursina import Button
        generation=self.generation
        button=Button(parent=self.layer,text='',position=(x,y,-1),scale=(w,h),
                      color=self.tint(ACCENT if primary else PANEL),highlight_color=self.tint('#81365e' if primary else '#bfdccf'),
                      pressed_color=self.tint('#683250' if primary else '#99c6b6'),radius=.12)
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

    def blocks_deployment(self,point):
        x,y=point[0],point[1]
        return x>.41 or y>.30 or y<-.34 or any(abs(x-b.x)<=b.scale_x/2 and abs(y-b.y)<=b.scale_y/2 for b in self.buttons)

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
            button.color=self.tint('#c3d8ed' if i==self.focus and button.base_tint!=ACCENT else button.base_tint)

    def input(self,key):
        if key in ('down arrow','tab'): self.focus_button(self.focus+1)
        elif key=='up arrow': self.focus_button(self.focus-1)
        elif key=='enter' and self.buttons: self.buttons[self.focus].on_click()
        elif self.route=='store': pass
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
                subtitle=f"金幣 {profile['coins']:,} 元     重生 {profile['rebirth_count']} 次     飛機上限 {(2+profile['rebirth_count'])} 架"
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
        self.text(f"重生 {profile['rebirth_count']} 次    /    敵機上限 {(2+profile['rebirth_count'])} 架",-.756,.086,.78,MUTED)
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

    def pager(self,page,pages,action,y=-.34):
        if page>0:self.button('上一頁',-.25,y,.25,.045,lambda:action(page-1),size=.75)
        self.text(f'{page+1} / {pages}',0,y+.012,.7,center=True)
        if page+1<pages:self.button('下一頁',.25,y,.25,.045,lambda:action(page+1),size=.75)

    def thumbnail(self,kind,key,x,y,scale=.05):
        from ursina import Entity,Texture
        from .models import thumbnail_texture
        appearance=('original','plain',())
        if kind=='weapon' and key in self.controller.state.profile['owned_weapons']:
            stats=resolve_weapon_stats(self.controller.state.profile,key);appearance=(stats.color_id,stats.pattern_id,stats.attachment_ids)
        texture=thumbnail_texture(kind,key,appearance,self.controller.settings.quality)
        return Entity(parent=self.layer,model='quad',texture=Texture(texture),position=(x,y,-2),scale=(scale*3.4,scale*3.4*2/3),add_to_scene_entities=False)

    def show_store(self):
        c=self.controller;p=c.state.profile
        self.heading(f"裝備庫  /  金幣 {p['coins']:,}",'準備你的糖果防線','購買及自訂後，於出戰準備選擇裝備。重生會清空本輪付費成果。')
        categories=[('player','自身升級'),('armor','裝甲'),('turret','自動防禦'),('weapon','槍枝')]
        for i,(key,label) in enumerate(categories):self.button(label,-.57+i*.38,.223,.35,.045,lambda k=key:c.store_select(k),primary=key==c.store_category,size=.8)
        if c.store_category=='player':
            level=p['player_upgrades']['max_hp'];self.text(f'生命強化  {level}/{upgrade_cap(p["rebirth_count"])}',-.6,.1,1)
            self.text(f'基本生命 {100+10*level} → {100+10*(level+1)}   下級 {250*(level+1)} 金幣',-.6,.025,.85)
            self.button('升級生命',0,-.1,.4,.07,lambda:c.shop_action('upgrade_player',upgrade_id='max_hp'),primary=True)
        else:
            if c.store_category=='weapon':
                filters=[('all','全部'),*CATEGORY_NAMES.items()]
                for i,(key,label) in enumerate(filters):self.button(label,-.665+i*.19,.163,.18,.035,lambda k=key:c.store_select(filter=k),primary=key==c.store_filter,size=.62)
                items=[w for w in ITEMS.values() if c.store_filter=='all' or w.category==c.store_filter]
            else:items=list(ARMORS.values() if c.store_category=='armor' else TURRETS.values())
            pages=max(1,(len(items)+5)//6);page=min(c.store_page,pages-1)
            for i,item in enumerate(items[page*6:page*6+6]):
                x=-.52+(i%3)*.52;y=.032-(i//3)*.197
                self.rect(x,y,.495,.182,PANEL);self.text(item.name,x-.226,y+.07,.70)
                self.thumbnail(c.store_category,item.id,x+.16,y+.005,.045)
                if c.store_category=='weapon':
                    owned=item.id in p['owned_weapons'];stats=resolve_weapon_stats(p,item.id) if owned else item
                    self.text(f'{MODE_NAMES[item.fire_mode]}  傷害 {stats.base_damage:.2f}\n射程 {stats.range:.0f}  間隔 {stats.interval:.2f}s',x-.226,y+.025,.63,MUTED)
                    self.button('自訂' if owned else f'購買 {item.price}',x-.08,y-.06,.25,.035,lambda w=item.id,o=owned:c.customize(w) if o else c.shop_action('purchase_weapon',weapon_id=w),size=.65)
                    self.button('預覽',x+.15,y-.06,.16,.035,lambda w=item.id:c.customize(w),size=.62)
                elif c.store_category=='armor':
                    owned=item.id in p['owned_armors'];self.text(f'生命 {item.hp_delta:+}  速度 ×{item.speed_factor}\n減傷 {item.damage_reduction}  回血 {item.regen_delay}s / {item.regen_rate}',x-.226,y+.025,.59,MUTED)
                    self.button('已擁有' if owned else f'購買 {item.price}',x,y-.06,.35,.035,lambda w=item.id:c.shop_action('purchase_armor',armor_id=w),size=.65)
                else:
                    count=sum(t['turret_id']==item.id for t in p['owned_turrets']);self.text(f'{"防空" if item.target_kind=="aircraft" else "對地"}  傷害 {item.damage}  射程 {item.range}\n間隔 {item.interval}s  庫存 {count}',x-.226,y+.025,.63,MUTED)
                    self.button('首次重生後開放' if p['rebirth_count']==0 else f'購買一台 {item.price}',x,y-.06,.43,.035,lambda w=item.id:c.shop_action('purchase_turret',turret_id=w),size=.62)
            self.pager(page,pages,lambda n:c.store_select(page=n))
        self.button('返回主選單',0,-.399,.34,.046,c.back,primary=True,size=.78)

    def show_weapon_customize(self):
        from copy import deepcopy
        c=self.controller;p=c.state.profile;wid=c.custom_weapon;w=ITEMS[wid];owned=p['owned_weapons'].get(wid)
        self.heading('武器工坊  /  '+w.id,w.name,'配件與外觀各武器獨立擁有；購買不會自動選用。')
        if owned:
            preview=deepcopy(p);draft=c.custom_draft
            preview['owned_weapons'][wid]=deepcopy(draft);stats=resolve_weapon_stats(preview,wid)
        else:stats=w
        info=f'{"已擁有" if owned else "尚未擁有"}  /  {w.price} 金幣\n基礎傷害 {w.base_damage:.2f} → {stats.base_damage:.2f}\n射程 {w.range:.0f} → {stats.range:.0f}m\n間隔 {w.interval:.3g} → {stats.interval:.3g}s\n彈匣 {stats.magazine_size or "∞"}  換彈 {stats.reload_seconds:.2f}s\n{MODE_NAMES[w.fire_mode]} / {CATEGORY_NAMES[w.category]} / 瞄準 ×{stats.aim_factor:.2f}'
        if w.category=='anti_air':info+=f'\n鎖定 {stats.lock_seconds:.2f}s / 白框 ×{stats.lock_box_scale:.2f}'
        if w.category=='rocket':info+=f'\n每關 {stats.quota} 發 / 爆炸半徑 {stats.blast_radius:.2f}m'
        if w.category=='shotgun':info+=f'\n每發 {stats.pellet_count} 彈丸 / 散角 {stats.spread_angle}°'
        self.text(info,-.74,.18,.72)
        self.preview_weapon(wid,stats)
        if not owned:
            self.button(f'購買 {w.price} 金幣',.3,-.12,.55,.065,lambda:c.shop_action('purchase_weapon',weapon_id=wid),primary=True)
            self.text('購買後即可升級、選配件與外觀。',.02,-.22,.7,MUTED)
        else:
            for i,(key,label) in enumerate([('upgrade','升級'),('attachment','配件'),('appearance','外觀')]):self.button(label,.01+i*.27,.21,.25,.045,lambda k=key:c.customize_tab(k),primary=key==c.custom_tab,size=.75)
            if c.custom_tab=='upgrade':
                keys=[k for k in UPGRADE_PRICES if applicable_upgrade(wid,k)]
                for i,key in enumerate(keys):
                    y=.137-i*.071;level=owned['upgrade_levels'][key];cap=1 if key=='aim_assist' else upgrade_cap(p['rebirth_count']);cost=UPGRADE_PRICES[key]*(level+1)
                    trial=deepcopy(preview);trial['owned_weapons'][wid]['upgrade_levels'][key]=min(level+1,cap);nextstats=resolve_weapon_stats(trial,wid)
                    field=dict(damage='base_damage',cooldown='interval',range='range',lock_time='lock_seconds',whitebox='lock_box_scale',aim_assist='aim_assist')[key]
                    effect=f'{getattr(stats,field):.2f} → {getattr(nextstats,field):.2f}'
                    if key=='aim_assist':effect=('開啟' if stats.aim_assist else '關閉')+' → 開啟'
                    self.text(f'{UPGRADE_NAMES[key]} {level}/{cap}  {effect}',-.1,y+.02,.66)
                    self.button('已滿' if level==cap else str(cost)+' 金幣',.63,y,.24,.045,lambda k=key:c.shop_action('upgrade_weapon',weapon_id=wid,upgrade_id=k),size=.64)
            elif c.custom_tab=='attachment':
                items=[a for a in ATTACHMENTS.values() if wid in a.applicable_weapons]
                for i,a in enumerate(items):
                    y=.125-i*.076;has=a.id in owned['owned_attachments'];selected=draft['selected_attachments'][a.slot]==a.id
                    self.text(a.name+' / '+a.slot,-.1,y+.026,.7)
                    detail={'zoom_scope':'倍率 ×1.5 / 換彈 ×1.10','guidance_scope':'白框 ×1.10 / 鎖定 ×1.10' if w.category=='anti_air' else '倍率 ×1.5 / 換彈 ×1.10','heavy_barrel':'傷害 ×1.15 / 間隔 ×1.10','extended_magazine':'彈匣 ×1.5 / 換彈 ×1.20','quick_reload':'換彈 ×0.80 / 彈匣 ×0.80','cooling_guidance':'間隔 ×0.85 / 鎖定 ×1.15','light_loading_rack':'裝填 ×0.85 / 半徑 ×0.85'}[a.id]
                    self.text(detail,-.1,y-.006,.56,MUTED)
                    self.button('拆下' if selected else '選用' if has else f'購買 {a.price}',.62,y,.24,.043,lambda a=a,h=has,sel=selected:c.custom_select('selected_attachments',None if sel else a.id,a.slot) if h else c.shop_action('purchase_attachment',weapon_id=wid,attachment_id=a.id),size=.62)
            else:
                for col,(kind,catalog,field,ownership,cost) in enumerate([('color',COLORS,'selected_color','owned_colors',75),('pattern',PATTERNS,'selected_pattern','owned_patterns',100)]):
                    for i,(key,name) in enumerate(catalog.items()):
                        y=.12-i*.077;has=key in owned[ownership];label=('✓ ' if draft[field]==key else '')+name+('' if has else f' {cost}')
                        self.button(label,.07+col*.45,y,.4,.052,lambda k=key,h=has,f=field,ck=kind:c.custom_select(f,k) if h else c.shop_action('purchase_cosmetic',weapon_id=wid,cosmetic_kind=ck,cosmetic_id=k),size=.67)
            self.button('套用自訂',.35,-.352,.5,.05,c.apply_custom,primary=True,size=.78)
        self.button('返回商店',-.47,-.395,.4,.05,c.back,size=.8)

    def preview_weapon(self,wid,stats):
        from .models import build_weapon
        from ursina import Entity
        pivot=Entity(parent=self.layer,position=(0,0,-1),rotation=(8,-110,-10),add_to_scene_entities=False)
        build_weapon(wid,getattr(stats,'color_id','original'),getattr(stats,'pattern_id','plain'),getattr(stats,'attachment_ids',()),parent=pivot)
        pivot.weapon_id=wid
        self.preview=pivot;pivot.preview_zoom=.8;self.frame_preview(pivot)
        def rotate():pivot.rotation_y+=30;self.frame_preview(pivot)
        def zoom():pivot.preview_zoom=min(1,pivot.preview_zoom+.1);self.frame_preview(pivot)
        self.button('旋轉',-.65,-.31,.19,.035,rotate,size=.65)
        self.button('放大',-.4,-.31,.19,.035,zoom,size=.65)

    def frame_preview(self,pivot):
        # 依旋轉後實際包絡取景，長彈匣與腳架不會跨入操作按鈕。
        pivot.position=(0,0,-1);pivot.scale=1
        low,high=pivot.getTightBounds(self.layer)
        pivot.scale=min(.60/max(.001,high.x-low.x),.22/max(.001,high.y-low.y))*pivot.preview_zoom
        low,high=pivot.getTightBounds(self.layer)
        pivot.x=-.47-(low.x+high.x)/2;pivot.y=-.155-(low.y+high.y)/2

    def prepare_footer(self):
        c=self.controller
        self.button('返回',-.27,-.395,.4,.05,c.back,size=.78)
        self.button('下一步',.27,-.395,.4,.05,c.prep_next,primary=True,size=.78)

    def show_prepare_armor(self):
        c=self.controller;p=c.state.profile;selected=c.state.draft.loadout['armor_id'];stats=resolve_player_stats(p,selected)
        self.heading('出戰準備  /  1 / 3','選擇裝甲',f'生命 {stats.max_hp}  移速 {stats.move_speed:.1f}  減傷 {stats.damage_reduction}  回血 {stats.regen_delay}s 後每秒 {stats.regen_rate}')
        self.button('✓ 不穿裝甲' if selected is None else '不穿裝甲',0,.205,.5,.05,lambda:c.prep_armor(None),primary=selected is None,size=.8)
        for i,a in enumerate(ARMORS.values()):
            x=-.5+(i%3)*.5;y=.075-(i//3)*.17
            self.rect(x,y,.47,.15,PANEL);self.text(a.name,x-.2,y+.05,.75);self.thumbnail('armor',a.id,x+.16,y+.005,.048)
            self.text(f'生命 {a.hp_delta:+}  速度 ×{a.speed_factor}\n減傷 {a.damage_reduction}  回血 {a.regen_delay}s / {a.regen_rate}',x-.2,y+.009,.6,MUTED)
            self.button('✓ 已選擇' if selected==a.id else '穿戴' if a.id in p['owned_armors'] else '尚未購買',x,y-.05,.37,.038,lambda k=a.id:c.prep_armor(k),primary=selected==a.id,size=.65)
        self.prepare_footer()

    def show_prepare_weapons(self):
        c=self.controller;p=c.state.profile;slots=c.state.draft.loadout['weapon_slots']
        self.heading('出戰準備  /  2 / 3','安排五個武器槽','至少一把防空及一把對地；空槽合法，同一把不可重複。')
        for i,k in enumerate(slots):self.button(f'{i+1} '+(ITEMS[k].name if k else '空槽'),-.63+i*.315,.21,.303,.055,lambda n=i+1:c.choose_prep_slot(n),primary=c.prep_slot==i+1,size=.61)
        items=list(p['owned_weapons']);page=min(getattr(self,'weapon_page',0),max(0,(len(items)-1)//6))
        for i,key in enumerate(items[page*6:page*6+6]):
            w=ITEMS[key];self.button(w.name,-.5+i%3*.5,.09-i//3*.14,.46,.10,lambda k=key:c.prep_weapon(k),size=.85)
        self.pager(page,max(1,(len(items)+5)//6),lambda n:self.set_weapon_page(n),y=-.22)
        self.button('清空此槽',-.4,-.306,.3,.045,lambda:c.prep_weapon(None),size=.75)
        self.button('向左換位',0,-.306,.3,.045,lambda:c.swap_prep_slot(-1),size=.75)
        self.button('向右換位',.4,-.306,.3,.045,lambda:c.swap_prep_slot(1),size=.75);self.prepare_footer()
    def set_weapon_page(self,page):self.weapon_page=page;self.show()

    def show_prepare_deployment(self):
        c=self.controller;p=c.state.profile;d=c.state.draft
        self.rect(0,.4,1.78,.2,INK);self.text(f'鳥瞰部署  /  {len(d.loadout["deployments"])} / {2*p["rebirth_count"]}',-.78,.46,1.3)
        self.text('WASD／中鍵平移 · 滾輪縮放 · 左鍵選取或放置 · 右鍵取消',-.78,.365,.7,MUTED)
        self.rect(.65,-.015,.48,.63,INK,alpha=.97)
        items=p['owned_turrets'];page=min(getattr(self,'tower_page',0),max(0,(len(items)-1)//5))
        if not items:self.text('首次重生後開放\n可零部署繼續',.435,.21,.76,MUTED)
        for i,t in enumerate(items[page*5:page*5+5]):self.button(TURRETS[t['turret_id']].name+' '+str(page*5+i+1),.65,.225-i*.067,.42,.05,lambda k=t['instance_id']:c.deploy_select(k),primary=c.deploy_selected==t['instance_id'],size=.64)
        if page>0:self.button('上頁',.53,-.145,.18,.04,lambda:self.set_tower_page(page-1),size=.6)
        if (page+1)*5<len(items):self.button('下頁',.76,-.145,.18,.04,lambda:self.set_tower_page(page+1),size=.6)
        self.button('移除所選',.65,-.206,.38,.045,c.deploy_remove,size=.68)
        for x,y,label,dx,dz in [(-.66,-.23,'←',-.3,0),(-.39,-.23,'→',.3,0),(-.525,-.16,'↑',0,.3),(-.525,-.3,'↓',0,-.3)]:self.button(label,x,y,.1,.042,lambda a=dx,b=dz:c.scene.deployment_pan(a,b),size=.7)
        self.button('＋',-.24,-.27,.12,.045,lambda:c.scene.deployment_zoom(.9),size=.7);self.button('－',-.09,-.27,.12,.045,lambda:c.scene.deployment_zoom(1/.9),size=.7)
        self.button('置中',.1,-.27,.2,.045,c.scene.deployment_center,size=.7)
        self.text('粉紅：敵軍通道  /  黃色：出生區',-.78,.32,.57,MUTED)
        self.text('綠點：可見  /  紅點：遮擋；水平射程預覽，防空依實際高度判定。',-.78,-.34,.60,MUTED)
        c.scene.sync_deployment(d,p,c.deploy_selected);self.prepare_footer()
    def set_tower_page(self,page):self.tower_page=page;self.show()

    def show_prepare_confirm(self):
        c=self.controller;p=c.state.profile;d=c.state.draft
        self.heading('出戰確認','糖果防線，準備出發',f'本關 {c.state.cursor[0]}-{c.state.cursor[1]}，確認配置保存成功後才開始。')
        self.text('裝甲：'+(ARMORS[d.loadout['armor_id']].name if d.loadout['armor_id'] else '不穿裝甲'),-.62,.18,1)
        for i,k in enumerate(d.loadout['weapon_slots']):self.text(f'{i+1}  '+(ITEMS[k].name if k else '空槽'),-.62,.11-i*.059,.85)
        self.text(f'砲塔：{len(d.loadout["deployments"])} / {2*p["rebirth_count"]}',.18,.12,.9)
        from .progression import difficulty_for, level_for
        level=level_for(*c.state.cursor,2+p['rebirth_count']);strength=difficulty_for(level)
        self.text(f'本關獎勵 {level.reward:,} 元\n敵機生命 ×{strength.air_hp_factor:g}\n敵兵生命 ×{strength.ground_hp_factor:g}\n移動 ×{strength.speed_factor:g}  轉向 ×{strength.turn_factor:g}',.18,.035,.77,MUTED)
        self.button('返回部署',-.27,-.34,.4,.07,c.back,size=.85);self.button('開始戰鬥',.27,-.34,.4,.07,c.confirm_start,primary=True,size=.85)

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
        self.text(f"確認後，全部金幣歸零。\n重生次數增為 {p['rebirth_count']+1}，敵機上限增為 {(3+p['rebirth_count'])}。\n全部已購武器、裝甲、砲塔、升級、配件與外觀清空。\n重新配發三把基礎武器，從 1-1 出發。",0,.14,1,WHITE,center=True)
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
        next_stage=f'{app.cursor[0]}-{app.cursor[1]}'
        self.heading(f"防守報告  /  {result['level']}",'防線守住了' if success else '防線遭到突破',
                     '所有敵機與敵兵已清除。' if success else ERRORS.get(result['reason'],'本局結束'))
        self.text(f"+ {result['reward']:,} 元" if success else '本局獎勵  0 元',0,.17,2.1,ACCENT,center=True)
        self.text(f"目前金幣 {app.profile['coins']:,} 元    下一次出擊 {next_stage}",0,.058,.92,MUTED,center=True)
        self.button(f'前往下一關（{next_stage}）' if success else '返回主選單',0,-.11,.62 if success else .53,.082,
                    self.controller.start if success else self.controller.show_menu,primary=True)
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
            self.hud['name'+str(slot)]=self.text(f'{slot}  空槽',x-.139,-.387,.66)
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
        self.hud['scope_range']=self.text('',0,-.312,.65,TEAL,parent=self.scope,center=True)
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
        self.set_text('regen',f'鎧甲 {p.armor}  ·  回血預算 {max(0,p.max_hp*.2-p.healed):.0f}  ·  '+('恢復中' if p.since_damage>=p.regen_delay and p.hp<p.max_hp and p.healed<p.max_hp*.2 else '掩護待命'))
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
        for slot,wid in enumerate(battle.loadout.weapon_slots,1):
            self.hud['slot'+str(slot)].color=self.tint('#bfdccf' if slot==p.weapon_slot else INK)
            self.set_text('name'+str(slot),f'{slot} '+(ITEMS[wid].name if wid else '空槽'))
            value='空槽'
            if wid:
                r=battle.runtime[wid];stats=battle.loadout.weapons[wid]
                value=f'{MODE_NAMES[stats.fire_mode]} '+('∞' if r.magazine_rounds is None else f'{r.magazine_rounds}/{stats.magazine_size}')
                if r.quota_remaining is not None:value+=f' 餘{r.quota_remaining}'
                if r.reload_finish_at is not None:value+=f' 裝填 {max(0,r.reload_finish_at-battle.elapsed):.1f}s'
                elif r.next_shot_at>battle.elapsed:value+=(' 上膛 ' if stats.fire_mode=='bolt' else ' 冷卻 ')+f'{r.next_shot_at-battle.elapsed:.1f}s'
            self.set_text('cd'+str(slot),value)
        self.set_text('scope_range',f'狙擊 / {battle.stats.range:.0f} m / ×{battle.stats.aim_factor:.1f}')
        kind='lock' if p.aiming and battle.stats.category=='anti_air' else 'scope' if p.aiming and battle.stats.category=='sniper' else 'crosshair'
        self.cross.enabled=kind=='crosshair'; self.scope.enabled=kind=='scope'; self.lock_root.enabled=kind=='lock'
        if kind=='lock':
            size=.21*battle.stats.lock_box_scale
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
