"""原生 3D 呈現適配；所有幾何與特效均不持有傷害邏輯。"""
from pathlib import Path
from math import sin, cos, pi
from random import Random
from .config import ASSETS, QUALITY

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
        self.deployment_saved=None;self.deployment_nodes=[];self.deployment_height=200;self.deployment_xy=[0,80];self.drag_point=None;self.core_tracers={}
        self.deployment_overlay=None;self.placement_ghost=None
        camera.fov=90
        camera.clip_plane_far=600
        camera.clip_plane_near=.05
        self.build_world()

    def part(self, parent, position=(0,0,0), scale=(1,1,1), tint='#596965', model='cube', **kwargs):
        from ursina import Entity, color
        from .models import rounded_mesh, sphere_mesh
        if model=='cube':model=rounded_mesh()
        elif model=='sphere':model=sphere_mesh()
        node=Entity(parent=parent,model=model,position=position,scale=scale,color=color.hex(tint),
                    shader=self.shader,add_to_scene_entities=False,**kwargs)
        if self.shader:
            node.set_shader_input('fog_color',color.hex('#b8dcf0'))
            node.set_shader_input('fog_start',180.)
            node.set_shader_input('fog_end',650.)
            node.set_shader_input('shadow_color',color.rgba32(22,38,42,115))
            node.set_shader_input('shadow_samples',2 if self.settings.quality=='high' else 1)
            node.set_shader_input('shadow_blur',.002)
        return node

    def build_world(self):
        from ursina import Entity, DirectionalLight, AmbientLight, color, Vec3, scene, window
        self.sun=DirectionalLight(shadows=False,rotation=(45,-35,0),color=color.hex('#c6bab5'))
        self.ambient=AmbientLight(color=color.rgba32(110,133,148,255))
        self._quality_key=None
        self.apply_quality(self.settings.quality)
        window.color=color.hex('#b8dcf0')
        scene.fog_color=color.hex('#b8dcf0')
        scene.fog_density=(180,480)
        from .deployment import WORLD
        left,right,bottom,top=WORLD.bounds;cx=(left+right)/2;cz=(bottom+top)/2
        self.part(self.root,(cx,-.7,cz),(right-left+80,1,top-bottom+60),'#a4cdb7')
        self.part(self.root,(cx,-.6,cz),(right-left,1,top-bottom),'#b8dec8',collider='box')
        self.part(self.root,(0,-.055,75),(36,.1,305),'#d0c6e8')
        self.part(self.root,(-19,0,75),(.3,.05,305),'#cebd89')
        self.part(self.root,(19,0,75),(.3,.05,305),'#cebd89')
        for z in range(-50,230,12):
            self.part(self.root,(0,.008,z),(.24,.03,4),'#c4b896')
        for x in (left,right): self.part(self.root,(x,1,cz),(1,2,top-bottom),'#b6d2e7',collider='box')
        for z in (bottom,top): self.part(self.root,(cx,1,z),(right-left,2,1),'#b6d2e7',collider='box')
        for center,size in WORLD.boxes[:-1]:
            x,y,z=center.tuple();w,h,d=size.tuple()
            self.part(self.root,(x,y,z),(w,h,d),'#ecb7d0',collider='box')
            self.part(self.root,(x,y+h*.5,z),(w+.25,.12,d+.25),'#f9dfa6')
            for offset in (-.3,.3): self.part(self.root,(x+w*offset,y,z-d*.5-.025),(.35,h*.65,.04),'#d4b16b')
        # 目標大樓與防禦區，碰撞尺寸與純規則模型一致。
        self.part(self.root,(0,10,-60),(18,20,14),'#94cfe2',collider='box')
        self.part(self.root,(0,20.2,-60),(20,.4,16),'#f6d493')
        self.part(self.root,(0,22,-60),(7,3.2,7),'#b5a0db')
        self.part(self.root,(0,24.7,-60),(.18,4,.18),'#dad9b6')
        for floor in range(2,20,3):
            self.part(self.root,(0,floor,-52.96),(17,.75,.07),'#bac9b7')
            for side in (-1,1): self.part(self.root,(9.03*side,floor,-60),(.07,.75,12),'#b4c3b3')
        for x in (-7,-3.5,0,3.5,7): self.part(self.root,(x,10,-52.88),(.16,20,.12),'#5f84a5')
        for i in range(64):
            angle=2*pi*i/64
            self.part(self.root,(cos(angle)*10,.04,-45+sin(angle)*10),(.5,.04,.16),'#d8b866',rotation_y=-angle*180/pi)
        rng=Random(781)
        for side in (-1,1):
            for z in range(-72,211,28):
                x=side*rng.uniform(72,84); height=rng.uniform(5,16)
                self.part(self.root,(x,height/2,z),(rng.uniform(6,10),height,10),'#c1afe1')
                self.part(self.root,(x,height+.2,z),(8,.4,10),'#f4cbda')
                for y in range(2,int(height),3): self.part(self.root,(x-side*4.1,y,z),(.08,.7,7),'#d6edf4')
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
                'fog_color':color.hex('#b8dcf0'),'fog_start':180.,'fog_end':650.}
        for key,value in inputs.items(): root.setShaderInput(ShaderInput(key,value,priority=1))

    def apply_quality(self,quality):
        import os
        from ursina.shaders import unlit_shader
        from .materials import candy_shader
        key=(quality,bool(os.environ.get('AIR_DEFENSE_NO_SHADER')))
        if key==self._quality_key: return
        self.settings.quality=quality
        # 基本材質保留 flattenStrong 烘焙的頂點色，不使用忽略頂點色的著色器。
        self.shader=unlit_shader
        self.shadows_enabled=False
        # 陰影相機／緩衝區至多建立一次；低畫質停止陰影繪製，
        # 保留一份可重用資源，避免每次切換重建。
        self.sun._light.setActive(False)
        if quality!='low' and not key[1]:
            try:
                if not self.sun._light.isShadowCaster():
                    self.sun.shadow_map_resolution=(1024,1024)
                    self.sun.shadows=True
                    self.sun._light.getLens().setFilmSize(140,220)
                    self.sun._light.getLens().setNearFar(1,450)
                    self.sun.position=(0,120,80)
                self.shader=candy_shader()
                self.shadows_enabled=True
                self.sun._light.setActive(True)
            except Exception as exc:
                self.assets.fallbacks.append('陰影回退：'+str(exc))
                self.sun._light.setActive(False)
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
            self.part(root,(side*(2.8 if boss or support else 1.7),-.35,0),(.65,.65,2),'#74b9c8')
            if support:
                self.part(root,(side*2.8,-.35,1.2),(.16,2.1,.15),'#e1d5ad')
                self.part(root,(side*2.8,-.35,1.21),(2.1,.16,.15),'#e1d5ad')
            if boss:
                self.part(root,(side*1.2,.3,-1.2),(.5,.65,3),'#b0a2ad')
                self.part(root,(side*3,-.7,1),(.3,.3,2.8),'#ba9a6a')
        if fast: self.part(root,(0,.1,-1),(4,.25,3),tint,rotation_y=35)
        root.flattenStrong()
        return root

    def enemy_model(self,enemy):
        from ursina import Entity
        from .models import build_character
        root=build_character('A05' if enemy.kind=='GROUND_BOSS' else None,parent=self.dynamic,boss=enemy.kind=='GROUND_BOSS')
        chute=Entity(parent=root,add_to_scene_entities=False)
        self.part(chute,(0,4.8,0),(3.4,1.1,2.8),'#f5c1d7',model='sphere')
        for x in (-1.25,1.25):self.part(chute,(x*.5,3.2,0),(.025,2.8,.025),'#f7e9bd',rotation_z=x*18)
        root.chute=chute;return root

    def turret_model(self,kind='T01'):
        from .models import build_turret
        return build_turret(kind,parent=self.dynamic)

    def weapon_model(self,stats,armor_id=None):
        from ursina import Entity,camera
        from .models import build_weapon,part
        from .visual_catalog import PALETTE
        if self.weapon:destroy_tree(self.weapon)
        root=Entity(parent=camera,position=(.32,-.29,.75),scale=.35,add_to_scene_entities=False)
        root.gun=build_weapon(stats.weapon_id,stats.color_id,stats.pattern_id,stats.attachment_ids,parent=root,quality=self.settings.quality)
        root.bolt_parts=[(node,node.z) for node in root.gun.children if getattr(node,"name","") in ("側槍機","泵動前護木")]
        root.feed_parts=[(node,node.y) for node in root.gun.children if getattr(node,'name','')=='供彈部件']
        arm=part(root,(.2,-.4,-.18),(.35,.27,.6),'#f3d1b6')
        if armor_id:part(root,(.2,-.4,-.25),(.39,.32,.3),list(PALETTE.values())[int(armor_id[-1])%5])
        self.weapon=root;self.weapon_slot=stats.weapon_id;self.apply_material(root)

    def sync(self, battle, dt, events=()):
        from ursina import camera, Entity, destroy, color
        player=battle.player
        camera.position=player.eye.tuple()
        camera.rotation=(player.pitch,player.yaw,0)
        camera.orthographic=False
        camera.fov=battle.fov
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
            if key not in self.visuals: self.visuals[key]=self.turret_model(t.turret_type_id)
            node=self.visuals[key]; node.position=t.position.tuple()
            target=battle.enemies.get(t.target_id) or battle.aircraft.get(t.target_id)
            if target: node.look_at((target.position.x,t.position.y,target.position.z))
        for key,m in (*battle.missiles.items(),*battle.rockets.items()):
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
        if self.weapon_slot!=battle.active_weapon_id or self.weapon is None:self.weapon_model(battle.stats,battle.loadout.player.armor_id)
        self.weapon.enabled=not (player.aiming and battle.stats.category=='sniper')
        runtime=battle.runtime[battle.active_weapon_id]
        self.weapon.rotation_z=25*sin(battle.elapsed*6) if runtime.reload_finish_at is not None else 0
        reload_progress=max(0,min(1,1-(runtime.reload_finish_at-battle.elapsed)/battle.stats.reload_seconds)) if runtime.reload_finish_at is not None else 0
        for node,y in self.weapon.feed_parts:node.y=y-.5*sin(pi*reload_progress)
        cycle=max(0,min(1,(runtime.next_shot_at-battle.elapsed)/battle.stats.interval))
        for node,z in self.weapon.bolt_parts:node.z=z-(.22*sin(pi*cycle) if not self.settings.reduced_motion else 0)
        if not self.settings.reduced_motion:
            self.recoil=max(0,self.recoil-dt*3)
            self.weapon.z=.75-self.recoil*.09
            self.weapon.rotation_x=-self.recoil*8
        else:
            self.recoil=0
            self.weapon.z=.75
            self.weapon.rotation_x=0
        for event in events:
            if event.get('attempt_id')!=battle.attempt_id:continue
            kind=event['kind']
            if kind=='weapon_fire': self.recoil=1
            if kind in ('destroyed','explosion','enemy_destroyed','hit'):
                self.effect(event['position'],kind)
            if kind in ('weapon_fire','turret_fire') and event.get('target'):
                source=event.get('source_id','player')
                for i,target in enumerate(event.get('endpoints',[event['target']])):
                    self.tracer(event['position'],target,f'{source}-{i}')
                    self.core_tracers[f'{source}-{i}'].life+=max(0,dt)
                from .entities import V3
                origin=V3(*event['position']);forward=(V3(*event['target'])-origin).normalized()
                key=source+'-muzzle';node=self.core_tracers.get(key)
                if node is None:node=self.part(self.dynamic,model='sphere',tint='#fff1bd');self.core_tracers[key]=node
                node.position=(origin+forward*.9+V3(.15,-.15,0)).tuple();node.scale=.11;node.enabled=True;node.life=.06+max(0,dt)
        if battle.phase=='active':
            for node in self.core_tracers.values():
                node.life=max(0,node.life-dt);node.enabled=node.life>0
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
        from .models import sphere_mesh
        node.model=sphere_mesh(); node.position=position; node.rotation=(0,0,0)
        node.scale=2 if kind in ('destroyed','explosion') else .25
        node.color=color.hex('#f5bb72'); node.alpha=.8
        node.life=node.duration=.45 if kind in ('destroyed','explosion') else .12
        node.effect_kind=kind; self.effects.append(node)

    def tracer(self,origin,target,source='player'):
        from ursina import Vec3,color
        node=self.core_tracers.get(source)
        if node is None:
            node=self.part(self.dynamic,tint='#fae6a0');self.core_tracers[source]=node
        node.enabled=True;start=Vec3(*origin);end=Vec3(*target)
        node.position=(start+end)/2;node.look_at(end);node.scale=(.025,.025,max(.01,(end-start).length()))
        node.life=.08
        # 每發來源保留核心彈道，不與額外粒子共用上限。

    def deployment_view(self):
        from ursina import camera,mouse,Entity,Mesh
        from .deployment import WORLD
        from .entities import angles
        if self.deployment_saved is None:
            self.deployment_saved=(camera.parent,camera.position,camera.rotation,camera.fov,camera.orthographic,mouse.locked,mouse.visible)
            self.deployment_overlay=Entity(parent=self.dynamic,add_to_scene_entities=False)
            # 保留區直接取自同一 WorldDefinition，僅於配置畫面呈現。
            for a,b in zip(WORLD.enemy_route,WORLD.enemy_route[1:]):
                delta=b-a;mid=(a+b)*.5
                self.part(self.deployment_overlay,(mid.x,.14,mid.z),(7,.015,delta.length()),'#ddaac2',rotation_y=angles(delta)[0])
            points=[(cos(i*pi/32)*1.5,.22,sin(i*pi/32)*1.5) for i in range(65)]
            self.placement_ghost=Entity(parent=self.deployment_overlay,model=Mesh(vertices=points,mode='line',thickness=5),add_to_scene_entities=False)
            self.part(self.deployment_overlay,(WORLD.player_spawn.x,.16,WORLD.player_spawn.z),(9,.02,9),'#ebd495',model='sphere')
            self.placement_ghost.enabled=False
        camera.orthographic=True;self.update_deployment_camera()

    def deployment_ghost(self,draft,selected,position):
        from ursina import color
        from .deployment import WORLD,validate_placement
        if self.placement_ghost is None:return
        self.placement_ghost.enabled=bool(selected and position)
        if not self.placement_ghost.enabled:return
        others=[p for p in draft.loadout['deployments'] if p['instance_id']!=selected]
        error=validate_placement(WORLD,(position.x,position.z),others)
        self.placement_ghost.position=(position.x,0,position.z)
        self.placement_ghost.color=color.hex('#d4577b' if error else '#287d69')

    def update_deployment_camera(self):
        from ursina import camera
        camera.position=(self.deployment_xy[0],220,self.deployment_xy[1]);camera.rotation=(90,0,0);camera.fov=self.deployment_height
    def deployment_zoom(self,factor):
        self.deployment_height=max(40,min(360,self.deployment_height*factor));self.update_deployment_camera()
    def deployment_pan(self,x,z):
        self.deployment_xy[0]=max(-60,min(60,self.deployment_xy[0]+x*self.deployment_height*.5));self.deployment_xy[1]=max(-80,min(240,self.deployment_xy[1]+z*self.deployment_height*.5));self.update_deployment_camera()
    def deployment_center(self):self.deployment_xy=[0,80];self.deployment_height=200;self.update_deployment_camera()
    def ground_point(self,point):
        from ursina import camera,scene,window
        from panda3d.core import Point2,Point3
        from .entities import V3
        near=Point3();far=Point3();aspect=window.aspect_ratio
        camera.orthographic_lens.extrude(Point2(point[0]*2/aspect,point[1]*2),near,far)
        start=scene.getRelativePoint(camera,near);end=scene.getRelativePoint(camera,far)
        if abs(end.y-start.y)<1e-9:return None
        t=-start.y/(end.y-start.y)
        return V3(start.x+(end.x-start.x)*t,0,start.z+(end.z-start.z)*t)
    def deployment_drag(self,point,held):
        current=self.ground_point(point) if held else None
        if held and self.drag_point is not None and current is not None:
            self.deployment_xy[0]=max(-60,min(60,self.deployment_xy[0]+self.drag_point.x-current.x));self.deployment_xy[1]=max(-80,min(240,self.deployment_xy[1]+self.drag_point.z-current.z));self.update_deployment_camera()
            current=self.ground_point(point)
        self.drag_point=current
    def sync_deployment(self,draft,profile,selected=None):
        from .catalog import TURRETS
        from .deployment import range_preview
        for node in self.deployment_nodes:destroy_tree(node)
        self.deployment_nodes=[];types={t['instance_id']:t['turret_id'] for t in profile['owned_turrets']}
        for p in draft.loadout['deployments']:
            node=self.turret_model(types[p['instance_id']]);node.position=(p['x'],0,p['z']);self.deployment_nodes.append(node)
            if p['instance_id']==selected:
                # 樣本合併為一份 Mesh，避免上千個更新節點。
                from ursina import Mesh,Entity,color
                from ursina.shaders import unlit_shader
                samples=range_preview((p['x'],p['z']),TURRETS[types[p['instance_id']]].range)
                vertices=[];triangles=[];colors=[]
                for x,z,visible in samples:
                    i=len(vertices);vertices.extend([(x-.3,.12,z-.3),(x+.3,.12,z-.3),(x+.3,.12,z+.3),(x-.3,.12,z+.3)]);triangles.extend([(i,i+2,i+1),(i,i+3,i+2)]);colors.extend([color.hex('#1b6945' if visible else '#b63756')]*4)
                self.deployment_nodes.append(Entity(parent=self.dynamic,model=Mesh(vertices=vertices,triangles=triangles,colors=colors),shader=unlit_shader,double_sided=True,add_to_scene_entities=False))
    def end_deployment(self):
        from ursina import camera,mouse,application
        for node in self.deployment_nodes:destroy_tree(node)
        self.deployment_nodes=[];self.drag_point=None
        if self.deployment_overlay is not None:destroy_tree(self.deployment_overlay)
        self.deployment_overlay=None;self.placement_ghost=None
        if self.deployment_saved:
            parent,pos,rot,fov,ortho,locked,visible=self.deployment_saved;camera.parent=parent;camera.orthographic=ortho;camera.position=pos;camera.rotation=rot;camera.fov=fov
            if application.window_type=='onscreen':mouse.locked=locked;mouse.visible=visible
            self.deployment_saved=None

    def menu_view(self):
        from ursina import camera
        camera.orthographic=False
        camera.position=(46,30,5)
        from .entities import angles, V3
        yaw,pitch=angles(V3(0,9,-55)-V3(46,30,5))
        camera.rotation=(pitch,yaw,0)
        camera.fov=65

    def teardown(self):
        from ursina import destroy
        self.end_deployment()
        for node in self.core_tracers.values():destroy_tree(node)
        self.core_tracers.clear()
        for entity in self.visuals.values(): destroy_tree(entity)
        self.visuals.clear()
        for entity in self.effects: destroy_tree(entity)
        self.effects.clear()
        if self.weapon: destroy_tree(self.weapon); self.weapon=None
        self.weapon_slot=None

    def metrics(self):
        return {'visuals':len(self.visuals),'effects':len(self.effects),'pooled_effects':len(self.effect_pool),
                'pooled_missiles':len(self.missile_pool),'temporary_ui':0}
