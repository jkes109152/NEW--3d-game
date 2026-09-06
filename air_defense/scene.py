"""原生 3D 呈現適配；所有幾何與特效均不持有傷害邏輯。"""
from pathlib import Path
from math import sin, cos, pi
from random import Random
from .config import ASSETS, COVERS, TURRET_POSITIONS, QUALITY

def destroy_tree(node):
    """Ursina 8.3 的 destroy 不遞迴登出子 Entity，因此明確由葉節點清理。"""
    from ursina import destroy
    for child in list(node.children): destroy_tree(child)
    destroy(node)

class AssetRegistry:
    def __init__(self, root=ASSETS):
        self.root=Path(root)
        self.fallbacks=[]

    def resolve(self, relative, fallback=None):
        path=self.root/relative
        if path.is_file(): return path
        self.fallbacks.append(str(relative))
        return fallback

    def material(self, color, **kwargs):
        return {'color':tuple(color),**kwargs}

class GameScene:
    def __init__(self, settings):
        from ursina import Entity, camera
        self.settings=settings
        self.assets=AssetRegistry()
        self.root=Entity()
        self.dynamic=Entity()
        self.visuals={}
        self.effects=[]
        self.effect_pool=[]
        self.missile_pool=[]
        self.weapon=None
        self.weapon_slot=None
        self.recoil=0.
        camera.fov=90
        camera.clip_plane_far=600
        camera.clip_plane_near=.05
        self.build_world()

    def part(self, parent, position=(0,0,0), scale=(1,1,1), tint='#596965', model='cube', **kwargs):
        from ursina import Entity, color
        node=Entity(parent=parent,model=model,position=position,scale=scale,color=color.hex(tint),
                    shader=self.shader,add_to_scene_entities=False,**kwargs)
        if self.shader:
            node.set_shader_input('fog_color',color.hex('#98afb6'))
            node.set_shader_input('fog_start',180.)
            node.set_shader_input('fog_end',650.)
            node.set_shader_input('shadow_color',color.rgba32(22,38,42,115))
            node.set_shader_input('shadow_samples',2 if self.settings.quality=='high' else 1)
            node.set_shader_input('shadow_blur',.002)
        return node

    def build_world(self):
        from ursina import Entity, DirectionalLight, AmbientLight, color, Vec3, scene, window
        self.sun=DirectionalLight(shadows=False,rotation=(45,-35,0),color=color.hex('#ffdeb5'))
        self.ambient=AmbientLight(color=color.rgba32(110,133,148,255))
        self._quality_key=None
        self.apply_quality(self.settings.quality)
        window.color=color.hex('#98afb6')
        scene.fog_color=color.hex('#98afb6')
        scene.fog_density=(180,480)
        self.part(self.root,(0,-.6,80),(120,1,320),'#626b58',collider='box')
        self.part(self.root,(0,-.055,75),(36,.1,305),'#434c4c')
        self.part(self.root,(-19,0,75),(.3,.05,305),'#cebd89')
        self.part(self.root,(19,0,75),(.3,.05,305),'#cebd89')
        for z in range(-50,230,12):
            self.part(self.root,(0,.008,z),(.24,.03,4),'#c4b896')
        for x in (-60,60): self.part(self.root,(x,1,80),(1,2,320),'#646c64',collider='box')
        for z in (-80,240): self.part(self.root,(0,1,z),(120,2,1),'#646c64',collider='box')
        for x,y,z,w,h,d in COVERS:
            self.part(self.root,(x,y,z),(w,h,d),'#92967a',collider='box')
            self.part(self.root,(x,y+h*.5,z),(w+.25,.12,d+.25),'#c0b691')
            for offset in (-.3,.3): self.part(self.root,(x+w*offset,y,z-d*.5-.025),(.35,h*.65,.04),'#d4b16b')
        # 目標大樓與防禦區，碰撞尺寸與純規則模型一致。
        self.part(self.root,(0,10,-60),(18,20,14),'#677d7d',collider='box')
        self.part(self.root,(0,20.2,-60),(20,.4,16),'#d5c9a4')
        self.part(self.root,(0,22,-60),(7,3.2,7),'#526764')
        self.part(self.root,(0,24.7,-60),(.18,4,.18),'#dad9b6')
        for floor in range(2,20,3):
            self.part(self.root,(0,floor,-52.96),(17,.75,.07),'#bac9b7')
            for side in (-1,1): self.part(self.root,(9.03*side,floor,-60),(.07,.75,12),'#b4c3b3')
        for x in (-7,-3.5,0,3.5,7): self.part(self.root,(x,10,-52.88),(.16,20,.12),'#374e50')
        for i in range(64):
            angle=2*pi*i/64
            self.part(self.root,(cos(angle)*10,.04,-45+sin(angle)*10),(.5,.04,.16),'#d8b866',rotation_y=-angle*180/pi)
        rng=Random(781)
        for side in (-1,1):
            for z in range(-72,211,28):
                x=side*rng.uniform(43,53); height=rng.uniform(5,16)
                self.part(self.root,(x,height/2,z),(rng.uniform(6,10),height,10),'#77817a')
                self.part(self.root,(x,height+.2,z),(8,.4,10),'#aaac91')
                for y in range(2,int(height),3): self.part(self.root,(x-side*4.1,y,z),(.08,.7,7),'#acb7a3')
        for x,_,z in TURRET_POSITIONS:
            self.part(self.root,(x,.04,z),(3,.08,3),'#9d956e')
            for offset in (-1,1): self.part(self.root,(x+offset,.09,z),(.12,.05,2),'#d1bc7f')
        self.root.flattenStrong()

    def apply_material(self,root):
        from panda3d.core import ShaderInput, ShaderAttrib, GeomNode
        from ursina import color
        # flattenStrong 可能把舊 ShaderAttrib 搬進幾何狀態；保留幾何／頂點色，清除舊材質覆寫。
        for node in root.findAllMatches('**'):
            if node!=root: node.setState(node.getState().removeAttrib(ShaderAttrib))
            if isinstance(node.node(),GeomNode):
                for index in range(node.node().getNumGeoms()):
                    node.node().setGeomState(index,node.node().getGeomState(index).removeAttrib(ShaderAttrib))
        root.shader=self.shader
        # 較高優先序同時覆蓋子節點與合併後 GeomState 裡的舊著色器。
        root.setShader(self.shader._shader,1)
        inputs={'shadow_samples':2 if self.settings.quality=='high' else 1,
                'shadow_blur':.002,'shadow_color':color.rgba32(22,38,42,115),
                'fog_color':color.hex('#98afb6'),'fog_start':180.,'fog_end':650.}
        for key,value in inputs.items(): root.setShaderInput(ShaderInput(key,value,priority=1))

    def apply_quality(self,quality):
        import os
        from ursina.shaders import lit_with_shadows_shader, unlit_shader
        key=(quality,bool(os.environ.get('AIR_DEFENSE_NO_SHADER')))
        if key==self._quality_key: return
        self.settings.quality=quality
        # 基本材質保留 flattenStrong 烘焙的頂點色，不使用忽略頂點色的著色器。
        self.shader=unlit_shader
        self.sun.shadows=False
        if quality!='low' and not key[1]:
            try:
                self.sun.shadow_map_resolution=(1024,1024)
                self.sun.shadows=True
                self.sun._light.getLens().setFilmSize(140,220)
                self.sun._light.getLens().setNearFar(1,450)
                self.sun.position=(0,120,80)
                self.shader=lit_with_shadows_shader
            except Exception as exc:
                self.assets.fallbacks.append('陰影回退：'+str(exc))
                self.sun.shadows=False
        for root in (self.root,self.dynamic,self.weapon):
            if root is not None: self.apply_material(root)
        self._quality_key=key

    def aircraft_model(self, kind, parent=None):
        from ursina import Entity
        root=Entity(parent=parent or self.dynamic,add_to_scene_entities=False)
        boss=kind=='ARMORED_BOSS'; support=kind=='MANPOWER_SUPPORT'; fast=kind=='FAST'
        tint='#72677d' if boss else '#a68c64' if support else '#597f91' if fast else '#9d7062'
        length=9 if boss else 8 if support else 5 if fast else 6
        width=12 if boss else 11 if support else 6 if fast else 8
        self.part(root,(0,0,0),(1.5 if boss or support else .9,.8,length),tint)
        self.part(root,(0,.45,length*.25),(.8,.5,1.4),'#2b444b')
        self.part(root,(0,0,.1),(width,.2,1.8 if support else 1.1),tint,rotation_y=0 if support else -12)
        self.part(root,(0,.2,-length*.4),(width*.4,.15,1),tint)
        self.part(root,(0,.8,-length*.39),(.18,1.7,1.3),tint,rotation_x=-18)
        for side in (-1,1):
            self.part(root,(side*width*.43,.14,.1),(.45,.1,1.2),'#e5d7b0')
            self.part(root,(side*(2.8 if boss or support else 1.7),-.35,0),(.65,.65,2),'#364c50')
            if support:
                self.part(root,(side*2.8,-.35,1.2),(.16,2.1,.15),'#e1d5ad')
                self.part(root,(side*2.8,-.35,1.21),(2.1,.16,.15),'#e1d5ad')
            if boss:
                self.part(root,(side*1.2,.3,-1.2),(.5,.65,3),'#b0a2ad')
                self.part(root,(side*3,-.7,1),(.3,.3,2.8),'#ba9a6a')
        if fast: self.part(root,(0,.1,-1),(4,.25,3),tint,rotation_y=35)
        root.flattenStrong()
        return root

    def enemy_model(self, enemy):
        from ursina import Entity
        root=Entity(parent=self.dynamic,add_to_scene_entities=False)
        body=Entity(parent=root,add_to_scene_entities=False)
        boss=enemy.kind=='GROUND_BOSS'; tint='#75576b' if boss else '#68795d'
        self.part(body,(0,1.05,0),(.62,.65,.38),tint)
        self.part(body,(0,1.28,-.03),(.68,.32,.48),'#a29576' if boss else '#43564d')
        self.part(body,(0,1.60,0),(.37,.35,.36),'#bdaf8d')
        self.part(body,(0,1.72,0),(.43,.16,.4),tint)
        self.part(body,(0,1.60,.195),(.31,.09,.05),'#2c484c')
        for side in (-1,1):
            self.part(body,(side*.18,.39,0),(.23,.72,.25),'#354a43')
            self.part(body,(side*.18,.08,.08),(.26,.16,.4),'#263937')
            self.part(body,(side*.31,1.06,.12),(.15,.5,.2),tint,rotation_x=-35)
        self.part(body,(.25,1.13,.4),(.12,.14,.7),'#273e43')
        if boss: self.part(body,(0,1.18,-.32),(.68,.7,.3),'#ac947a')
        body.flattenStrong()
        chute=Entity(parent=root,add_to_scene_entities=False)
        self.part(chute,(0,4.8,0),(3.4,1.1,2.8),'#c3b895',model='sphere')
        for x in (-1.25,1.25):
            self.part(chute,(x*.5,3.2,0),(.025,2.8,.025),'#dbd5b6',rotation_z=x*18)
        chute.flattenStrong()
        root.chute=chute
        return root

    def turret_model(self):
        from ursina import Entity
        root=Entity(parent=self.dynamic,add_to_scene_entities=False)
        self.part(root,(0,.25,0),(1.7,.5,1.7),'#495e54')
        self.part(root,(0,.8,0),(.65,.9,.65),'#6b7d63')
        self.part(root,(0,1.2,.1),(1,.5,1),'#8c9975')
        for x in (-.27,.27): self.part(root,(x,1.2,.95),(.13,.13,1.4),'#293f41')
        root.flattenStrong()
        return root

    def weapon_model(self, slot):
        from ursina import Entity, camera, destroy
        if self.weapon: destroy_tree(self.weapon)
        root=Entity(parent=camera,position=(.32,-.29,.75),scale=.5,add_to_scene_entities=False)
        self.weapon=root; self.weapon_slot=slot
        self.part(root,(0,0,.2),(.28,.26,.85),'#364d50')
        self.part(root,(0,-.22,-.04),(.17,.32,.20),'#ae9874',rotation_x=-12)
        self.part(root,(0,.1,.1),(.29,.07,.5),'#b9b791')
        length={1:1.0,2:1.4,3:.38,4:1.2,5:1.0}[slot]
        self.part(root,(0,0,.6+length/2),(.12,.12,length),'#273c42')
        if slot in (1,5):
            for side in (-1,1): self.part(root,(side*.21,.04,.4),(.18,.18,1.1),'#7f927f')
            self.part(root,(0,.23,.13),(.38,.26,.13),'#91b8a0')
        if slot==2:
            self.part(root,(0,.27,.3),(.18,.18,.55),'#425c5e')
            self.part(root,(0,.27,.61),(.21,.21,.08),'#9bccc0')
        if slot==4:
            self.part(root,(0,.03,.5),(.5,.42,1.8),'#748b62')
            self.part(root,(0,.03,1.4),(.6,.55,.12),'#263f42')
        if slot==5:
            for side in (-1,1): self.part(root,(side*.32,.15,.2),(.15,.2,.65),'#bc9c6c')
        self.part(root,(.05,-.28,-.15),(.28,.22,.4),'#8c957b')
        root.flattenStrong()
        self.apply_material(root)

    def sync(self, battle, dt, events=()):
        from ursina import camera, Entity, destroy, color
        player=battle.player
        camera.position=player.eye.tuple()
        camera.rotation=(player.pitch,player.yaw,0)
        camera.fov=38 if player.aiming and player.weapon_slot==2 else 90
        battle.fov=camera.fov
        needed=set()
        for key,a in battle.aircraft.items():
            if a.hp<=0: continue
            needed.add(key)
            if key not in self.visuals: self.visuals[key]=self.aircraft_model(a.kind)
            node=self.visuals[key]; node.position=a.position.tuple(); node.rotation=(a.pitch,a.yaw,0)
        for key,e in battle.enemies.items():
            if e.hp<=0: continue
            needed.add(key)
            if key not in self.visuals: self.visuals[key]=self.enemy_model(e)
            node=self.visuals[key]; node.position=e.position.tuple(); node.rotation_y=e.yaw
            node.chute.enabled=e.phase=='descending'
        for key,t in battle.turrets.items():
            needed.add(key)
            if key not in self.visuals: self.visuals[key]=self.turret_model()
            node=self.visuals[key]; node.position=t.position.tuple()
            target=battle.enemies.get(t.target_id)
            if target: node.look_at((target.position.x,t.position.y,target.position.z))
        for key,m in battle.missiles.items():
            needed.add(key)
            if key not in self.visuals:
                node=self.missile_pool.pop() if self.missile_pool else self.part(self.dynamic,scale=(.12,.12,1.2),tint='#f8d491')
                node.enabled=True; node.is_missile=True; self.visuals[key]=node
            node=self.visuals[key]; node.position=m.position.tuple(); node.look_at((m.position+m.forward).tuple())
        for key in list(self.visuals):
            if key not in needed:
                node=self.visuals.pop(key)
                if getattr(node,'is_missile',False): node.enabled=False; self.missile_pool.append(node)
                else: destroy_tree(node)
        if self.weapon_slot!=player.weapon_slot or self.weapon is None: self.weapon_model(player.weapon_slot)
        self.weapon.enabled=not (player.aiming and player.weapon_slot==2)
        if not self.settings.reduced_motion:
            self.recoil=max(0,self.recoil-dt*3)
            self.weapon.z=.75-self.recoil*.09
            self.weapon.rotation_x=-self.recoil*8
        else:
            self.recoil=0
            self.weapon.z=.75
            self.weapon.rotation_x=0
        for event in events:
            kind=event['kind']
            if kind=='weapon_fire': self.recoil=1
            if kind in ('destroyed','explosion','enemy_destroyed','hit'):
                self.effect(event['position'],kind)
            if kind in ('weapon_fire','turret_fire') and event.get('target'):
                self.tracer(event['position'],event['target'])
        if battle.phase=='active':
            for node in self.effects[:]:
                node.life-=dt
                if node.life<=0:
                    self.effects.remove(node); node.enabled=False; self.effect_pool.append(node)
                elif node.effect_kind!='tracer':
                    node.scale*=1+dt*2
                    node.alpha=node.life/node.duration*.7

    def pooled_effect(self):
        if len(self.effects)>=QUALITY[self.settings.quality]['effects']: return None
        if self.effect_pool:
            node=self.effect_pool.pop(); node.enabled=True; return node
        return self.part(self.dynamic,tint='#f5bc72',model='sphere')

    def effect(self, position, kind):
        from ursina import color
        node=self.pooled_effect()
        if node is None: return
        node.model='sphere'; node.position=position; node.rotation=(0,0,0)
        node.scale=2 if kind in ('destroyed','explosion') else .25
        node.color=color.hex('#f5bb72'); node.alpha=.8
        node.life=node.duration=.45 if kind in ('destroyed','explosion') else .12
        node.effect_kind=kind; self.effects.append(node)

    def tracer(self, origin, target):
        from ursina import Vec3, color
        node=self.pooled_effect()
        if node is None: return
        start=Vec3(*origin); end=Vec3(*target)
        node.model='cube'; node.position=(start+end)/2; node.look_at(end)
        node.scale=(.025,.025,(end-start).length()); node.color=color.hex('#ffe5a2'); node.alpha=.8
        node.life=node.duration=.08; node.effect_kind='tracer'; self.effects.append(node)

    def menu_view(self):
        from ursina import camera
        camera.position=(46,30,5)
        from .entities import angles, V3
        yaw,pitch=angles(V3(0,9,-55)-V3(46,30,5))
        camera.rotation=(pitch,yaw,0)
        camera.fov=65

    def teardown(self):
        from ursina import destroy
        for entity in self.visuals.values(): destroy_tree(entity)
        self.visuals.clear()
        for entity in self.effects: destroy_tree(entity)
        self.effects.clear()
        if self.weapon: destroy_tree(self.weapon); self.weapon=None
        self.weapon_slot=None

    def metrics(self):
        return {'visuals':len(self.visuals),'effects':len(self.effects),'pooled_effects':len(self.effect_pool),
                'pooled_missiles':len(self.missile_pool),'temporary_ui':0}
