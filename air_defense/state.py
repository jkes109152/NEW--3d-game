"""當局模擬與應用流程：狀態、時間、交易都有唯一來源。"""
from copy import deepcopy
from dataclasses import dataclass, replace
from math import cos, sin, tau
from random import Random
import uuid
from .config import AIR_START, MAX_STEPS, TICK
from .combat import LockState, target_in_box, turret_damage, can_fire
from .entities import Aircraft, City, Enemy, Missile, Player, Turret, V3, clamp, visible_between
from .progression import level_for, next_level
from .save_data import SaveError, SlotRepository


from math import radians, tan
from dataclasses import asdict
from .catalog import WEAPONS as WEAPON_CATALOG, TURRETS, MODE_NAMES
from .loadout import resolve_loadout
from .weapons import WeaponRuntime, InputCommand
from .projectiles import Rocket, raycast_hit, explosion_targets
from .deployment import visible as world_visible
from .progression import difficulty_for

@dataclass(frozen=True)
class InputFrame:
    move_x:float=0
    move_z:float=0
    look_delta:tuple=(0,0)
    commands:tuple=()
    jump_pressed:bool=False
    fire_pressed:bool=False
    aim_held:bool | None=None
    weapon_slot:int | None=None
    pause_requested:bool=False
    visible_aircraft:tuple | None=None

@dataclass
class SimulationClock:
    accumulator: float = 0
    dropped_steps: int = 0

    def steps(self, dt):
        if dt<=0: return 0
        self.accumulator+=min(.1,dt)
        available=int((self.accumulator+1e-10)/TICK)
        count=min(available,MAX_STEPS)
        self.dropped_steps+=max(0,available-count)+int(max(0,dt-.1)/TICK)
        self.accumulator=max(0,self.accumulator-available*TICK)
        return count


class BattleState:
    def __init__(self,profile,level,seed=1701,attempt_id=None,missile_factory=Missile,loadout_snapshot=None):
        self.profile=deepcopy(profile);self.level=level;self.attempt_id=attempt_id or uuid.uuid4().hex
        self.loadout=loadout_snapshot or resolve_loadout(profile);self.runtime={k:WeaponRuntime.create(v) for k,v in self.loadout.weapons.items()}
        self.clock=SimulationClock();self.phase='active';self.elapsed=0.;self.difficulty=difficulty_for(level)
        stats=self.loadout.player
        self.player=Player(hp=stats.max_hp,max_hp=stats.max_hp,armor=stats.damage_reduction,move_speed=stats.move_speed,jump_height=stats.jump_height,regen_delay=stats.regen_delay,regen_rate=stats.regen_rate)
        self.player.weapon_slot=next(i+1 for i,k in enumerate(self.loadout.weapon_slots) if k)
        self.city=City();self.aircraft={}
        from .config import AIRCRAFT
        for i,kind in enumerate(level.roster):
            key=f'{self.attempt_id}-air-{i}';offset=(i-(len(level.roster)-1)/2)*10
            self.aircraft[key]=Aircraft(key,kind,V3(AIR_START[0]+offset,AIR_START[1],AIR_START[2]),hp=self.difficulty.hp(AIRCRAFT[kind][0],True),formation_offset=offset,speed_factor=self.difficulty.speed_factor,turn_factor=self.difficulty.turn_factor)
        self.enemies={};self.turrets={key:Turret(key,V3(x,0,z),turret_type_id=definition.id) for key,definition,x,z in self.loadout.deployments}
        self.missiles={};self.rockets={};self.missile_factory=missile_factory;self.lock=LockState();self.events=[];self.sequence=0;self.revision=0
        self.failure_reason=None;self.rng=Random(seed);self.drop_seeds={key:self.rng.getrandbits(64) for key in self.aircraft};self.shot_number=0
        self.aspect=16/9;self.last_error=None;self.processed_hits=set();self.pending_commands=[];self.pending_look=(0,0);self.held=False;self.require_release=False;self.last_command=-1

    @property
    def active_weapon_id(self):return self.loadout.weapon_slots[self.player.weapon_slot-1]
    @property
    def stats(self):return self.loadout.weapons[self.active_weapon_id]
    @property
    def fov(self):return 90/self.stats.aim_factor if self.player.aiming else 90

    def emit(self,kind,**payload):
        self.sequence+=1
        self.events.append(dict(kind=kind,attempt_id=self.attempt_id,sequence=self.sequence,source_id=payload.pop('source_id',self.active_weapon_id),**payload))
    def accept_event(self,event):return self.phase=='active' and event.get('attempt_id')==self.attempt_id

    def select_weapon(self,slot):
        if type(slot) is not int or not 1<=slot<=5 or not self.loadout.weapon_slots[slot-1]:return 'weapon_locked'
        if slot!=self.player.weapon_slot:
            self.runtime[self.active_weapon_id].cancel();self.player.weapon_slot=slot;self.player.aiming=False;self.lock.clear()
            self.runtime[self.active_weapon_id].next_shot_at=max(self.elapsed,self.runtime[self.active_weapon_id].next_shot_at)
        return 'applied'
    def toggle_aim(self):
        self.player.aiming=not self.player.aiming
        if not self.player.aiming:self.lock.clear()

    def candidates(self,multiplier=1):
        if self.stats.category!='anti_air':return ()
        size=.21*self.stats.lock_box_scale*multiplier
        return tuple(k for k,a in self.aircraft.items() if a.hp>0 and a.status=='approaching' and (a.position-self.player.position).horizontal().length()<=self.stats.range+1e-9 and target_in_box(self.player,a.position,size,self.aspect,self.fov) and world_visible(self.player.eye,a.position))

    def advance(self,dt,frame=None):
        self.events=[];frame=frame or InputFrame()
        if frame.pause_requested or any(c.kind=='pause' for c in frame.commands):self.pause();return self.snapshot()
        if self.phase!='active':return self.snapshot()
        self.pending_commands.extend(frame.commands)
        if frame.aim_held is not None:self.pending_aim=frame.aim_held
        self.pending_look=tuple(a+b for a,b in zip(self.pending_look,frame.look_delta))
        count=self.clock.steps(dt)
        if not count:return self.snapshot()
        for i in range(count):
            cmds=tuple(self.pending_commands) if i==0 else ()
            if i==0:self.pending_commands=[]
            current=replace(frame,commands=cmds,aim_held=getattr(self,'pending_aim',None) if i==0 else None,look_delta=self.pending_look if i==0 else (0,0),fire_pressed=frame.fire_pressed and i==0,jump_pressed=frame.jump_pressed and i==0,weapon_slot=frame.weapon_slot if i==0 else None)
            self.step(TICK,current)
            if i==0:self.pending_look=(0,0);self.pending_aim=None
            if self.phase!='active':break
        return self.snapshot()

    def step(self,dt,frame=None):
        if self.phase!='active' or dt<=0:return
        frame=frame or InputFrame()
        if frame.pause_requested or any(c.kind=='pause' for c in frame.commands):self.pause();return
        self.elapsed+=dt;self.revision+=1;self.processed_hits.clear();player=self.player
        player.yaw+=frame.look_delta[0];player.pitch=clamp(player.pitch+frame.look_delta[1],-85,85)
        if frame.aim_held is not None:player.aiming=frame.aim_held
        player.tick(dt);player.move(clamp(frame.move_x,-1,1),clamp(frame.move_z,-1,1),frame.jump_pressed,dt)
        for key,runtime in self.runtime.items():
            if runtime.tick(self.elapsed,self.loadout.weapons[key]):self.emit('reload_finished',weapon_id=key)
        for aircraft in self.aircraft.values():
            aircraft.update(dt)
            if aircraft.status=='impact':self.fail('impact');return
        for enemy in self.enemies.values():enemy.update(dt,player)
        for enemy in self.enemies.values():
            if enemy.hp<=0 or enemy.phase!='ground':continue
            if (enemy.position-self.city.position).horizontal().length()<=10:self.city.hp=max(0,self.city.hp-10*dt)
            if self.city.hp<=0:self.fail('city');return
            if enemy.cooldown<=1e-9 and (enemy.position-player.position).horizontal().length()<=38 and world_visible(enemy.center,player.eye):
                self.emit('player_hurt',damage=player.hurt(8),position=enemy.center.tuple());enemy.cooldown=1.5
            if player.hp<=0:self.fail('player');return
            if self.city.hp<=0:self.fail('city');return
        if self.stats.category=='anti_air':
            candidates=self.candidates()
            if self.stats.aim_assist and player.aiming:
                ids=self.candidates(1.5)
                if ids:
                    from .entities import angles
                    yaw,pitch=angles(self.aircraft[ids[0]].position-player.eye);dx=(yaw-player.yaw+180)%360-180;dy=pitch-player.pitch;length=(dx*dx+dy*dy)**.5;factor=min(1,3*dt/max(length,1e-9));player.yaw+=dx*factor;player.pitch+=dy*factor;candidates=self.candidates()
            alive={k for k,a in self.aircraft.items() if a.hp>0 and a.status=='approaching'};before=self.lock.ready()
            self.lock.update(dt,candidates,alive,player.aiming,self.stats.fire_mode=='lock_multi',self.stats.lock_seconds)
            if self.lock.ready() and not before:self.emit('lock_complete')
        else:self.lock.clear()
        if frame.weapon_slot:self.select_weapon(frame.weapon_slot)
        for cmd in sorted(frame.commands,key=lambda c:c.sequence):
            if cmd.sequence<=self.last_command:continue
            self.last_command=cmd.sequence
            if cmd.kind=='fire_up':self.held=False;self.require_release=False
            elif cmd.kind=='fire_down':
                if not self.held and not self.require_release:self.held=True;self.trigger()
            elif cmd.kind=='select_slot':self.select_weapon(cmd.value)
            elif cmd.kind=='toggle_aim':self.toggle_aim()
            elif cmd.kind=='reload':self.reload()
            elif cmd.kind=='jump' and player.position.y<=1e-6:player.vertical_speed=(2*18*player.jump_height)**.5
        if frame.fire_pressed:self.trigger()
        runtime=self.runtime[self.active_weapon_id];stats=self.stats
        while runtime.burst_remaining and runtime.error(self.elapsed) is None:
            at=runtime.next_shot_at
            if self.fire(at=at)!='applied':break
            runtime.burst_remaining=max(0,runtime.burst_remaining-1)
        if self.held and not self.require_release and stats.fire_mode=='auto':
            while runtime.error(self.elapsed) is None:
                if self.fire(at=runtime.next_shot_at)!='applied':break
        self.tick_turrets(dt)
        for key,missile in list(self.missiles.items()):
            status=missile.update(dt,self.aircraft.get(missile.target_id))
            if status=='hit':self.damage_aircraft(missile.target_id,missile.damage,missile.id)
            if status!='flying':self.missiles.pop(key,None)
        for key,rocket in list(self.rockets.items()):
            hit,status=rocket.update(dt,self.enemies.values())
            if hit:
                for e in explosion_targets(hit,rocket.blast_radius,self.enemies.values()):self.damage_enemy(e.id,rocket.damage,rocket.id)
                self.emit('explosion',position=hit.point.tuple(),weapon_id=rocket.weapon_id)
            if status!='flying':self.rockets.pop(key,None)
        self.check_outcome()
        for key in list(self.enemies):
            if self.enemies[key].hp<=0:del self.enemies[key]
        for slot,wid in enumerate(self.loadout.weapon_slots,1):self.player.cooldowns[slot]=max(0,self.runtime[wid].next_shot_at-self.elapsed) if wid else 0
        self.player.rpg_ammo=self.runtime[self.active_weapon_id].quota_remaining or 0

    def reload(self):
        runtime=self.runtime[self.active_weapon_id]
        if runtime.reload(self.elapsed,self.stats):self.emit('reload_started',weapon_id=self.active_weapon_id);return True
        return False
    def trigger(self):
        runtime=self.runtime[self.active_weapon_id]
        if self.stats.fire_mode=='burst' and (runtime.burst_remaining or self.elapsed+1e-9<runtime.next_burst_start_at):return 'cooldown'
        result=self.fire()
        if result=='applied' and self.stats.fire_mode=='burst':
            runtime.burst_remaining=min(2,runtime.magazine_rounds or 0);runtime.next_burst_start_at=self.elapsed+self.stats.burst_interval
        return result

    def fire(self,target_id=None,visible=True,ray_distance=None,at=None):
        if self.phase!='active':return 'phase'
        stats=self.stats;runtime=self.runtime[self.active_weapon_id];error=can_fire(self,runtime)
        if error:
            if error=='ammo':self.reload()
            self.last_error=error;self.emit('error',code=error);return error
        self.shot_number+=1;shot=f'{self.attempt_id}-shot-{self.shot_number}';origin=self.player.eye;forward=self.player.forward;endpoints=[]
        if stats.delivery=='homing':
            targets=self.lock.valid if stats.fire_mode=='lock_multi' else self.lock.valid[:1]
            if any(k not in self.candidates() for k in targets):return 'lock'
            pending={}
            try:
                for i,key in enumerate(targets):
                    mid=f'{shot}-{i}';missile=self.missile_factory(mid,key,origin,forward);missile.damage=stats.base_damage;missile.weapon_id=stats.weapon_id;pending[mid]=missile
            except Exception:self.emit('error',code='launch_failed');return 'launch_failed'
            self.missiles.update(pending);self.lock.clear();endpoints=[self.aircraft[k].position.tuple() for k in targets];self.emit('missile_launch',position=origin.tuple())
        elif stats.delivery=='rocket':
            self.rockets[shot]=Rocket(shot,stats.weapon_id,origin,forward,stats.projectile_speed,stats.range,stats.projectile_lifetime,stats.base_damage,stats.blast_radius)
            endpoints=[(origin+forward*stats.range).tuple()]
        else:
            from .entities import direction
            right=direction(self.player.yaw+90);up=V3(forward.y*right.z,forward.z*right.x-forward.x*right.z,-forward.y*right.x)
            for i in range(stats.pellet_count):
                ray=forward if i==0 else (forward+(right*cos((i-1)*tau/7)+up*sin((i-1)*tau/7))*tan(radians(stats.spread_angle))).normalized()
                hit=raycast_hit(origin,ray,stats.range,self.enemies.values());endpoints.append((hit.point if hit else origin+ray*stats.range).tuple())
                if hit and hit.kind=='enemy':self.damage_enemy(hit.target_id,stats.base_damage,(shot,i))
        runtime.consume(self.elapsed if at is None else at,stats)
        self.emit('weapon_fire',weapon_id=stats.weapon_id,weapon_slot=self.player.weapon_slot,position=origin.tuple(),target=endpoints[0],endpoints=endpoints,audio_key={'anti_air':'aa','rocket':'rpg'}.get(stats.category,stats.category))
        if stats.fire_mode=='bolt':self.emit('bolt_cycled',weapon_id=stats.weapon_id)
        if runtime.magazine_rounds==0:self.reload()
        self.last_error=None;return 'applied'

    def tick_turrets(self,dt):
        for turret in self.turrets.values():
            definition=TURRETS[turret.turret_type_id];turret.cooldown=max(0,turret.cooldown-dt)
            pool=self.aircraft.values() if definition.target_kind=='aircraft' else self.enemies.values()
            targets=[e for e in pool if e.hp>0 and (getattr(e,'status',None)=='approaching' if definition.target_kind=='aircraft' else e.phase=='ground' and (e.kind!='GROUND_BOSS' or e.hp>e.max_hp/2)) and (e.center-turret.center).horizontal().length()<=definition.range+1e-9 and world_visible(turret.center,e.center)]
            target=min(targets,key=lambda e:((e.center-turret.center).horizontal().length(),e.id)) if targets else None
            if not target:turret.target_id=None;turret.visible_since=None;continue
            if turret.target_id!=target.id:turret.target_id=target.id;turret.visible_since=self.elapsed
            if turret.visible_since is None:turret.visible_since=self.elapsed
            if turret.cooldown>1e-9 or self.elapsed-turret.visible_since+1e-9<definition.lock_seconds:continue
            self.shot_number+=1;key=f'{self.attempt_id}-tower-{self.shot_number}'
            if definition.target_kind=='aircraft':
                self.missiles[key]=Missile(key,target.id,turret.center,(target.center-turret.center).normalized(),damage=definition.damage,weapon_id=definition.id)
            else:self.damage_enemy(target.id,turret_damage(target,definition.damage),key)
            turret.cooldown=definition.interval;turret.visible_since=self.elapsed;self.emit('turret_fire',source_id=turret.id,position=turret.center.tuple(),target=target.center.tuple())

    def damage_aircraft(self, key, amount, source=None):
        aircraft=self.aircraft.get(key)
        if self.phase!='active' or aircraft is None or aircraft.hp<=0: return False
        if source is not None and (source,key) in self.processed_hits: return False
        if source is not None: self.processed_hits.add((source,key))
        aircraft.hp=max(0,aircraft.hp-amount)
        self.emit('hit',position=aircraft.position.tuple(),target_id=key)
        if aircraft.hp>0: return True
        aircraft.status='destroyed'
        aircraft.drop_batch_id='drop-'+key
        rng=Random(self.drop_seeds[key])
        count={'NORMAL':rng.randint(0,3),'MANPOWER_SUPPORT':6,'FAST':0,'ARMORED_BOSS':1}[aircraft.kind]
        for i in range(count):
            angle=rng.random()*tau
            radius=rng.random()*2.5
            pos=aircraft.position+V3(cos(angle)*radius,0,sin(angle)*radius)
            enemy_id=f'{key}-crew-{i}'
            kind='GROUND_BOSS' if aircraft.kind=='ARMORED_BOSS' else 'NORMAL'
            self.enemies[enemy_id]=Enemy(enemy_id,kind,pos,source_batch_id=aircraft.drop_batch_id,role=i%2,effective_max_hp=self.difficulty.hp(10 if kind=='GROUND_BOSS' else 3))
        self.emit('destroyed',position=aircraft.position.tuple(),target_id=key)
        self.emit('drop_created',source_id=key,count=count)
        return True

    def damage_enemy(self, key, amount, source=None):
        enemy=self.enemies.get(key)
        if self.phase!='active' or enemy is None or enemy.hp<=0: return False
        if source is not None and (source,key) in self.processed_hits: return False
        if source is not None: self.processed_hits.add((source,key))
        enemy.hp=max(0,enemy.hp-amount)
        self.emit('hit',position=enemy.center.tuple(),target_id=key)
        if enemy.hp<=0:
            enemy.phase='dead'
            self.emit('enemy_destroyed',position=enemy.center.tuple(),target_id=key)
        return True

    def fail(self,reason):
        if self.phase!='active':return
        self.phase='failure';self.failure_reason=reason;self.emit('failure',reason=reason);self.clear_transients()
    def check_outcome(self):
        if self.phase!='active':return
        if self.player.hp<=0:self.fail('player')
        elif self.city.hp<=0:self.fail('city')
        elif all(a.status=='destroyed' for a in self.aircraft.values()) and all(e.hp<=0 for e in self.enemies.values()):
            self.phase='success';self.emit('success',reward=self.level.reward);self.clear_transients()
    def pause(self):
        if self.phase=='active':self.phase='paused'
        self.clock.accumulator=0;self.pending_commands=[];self.pending_look=(0,0);self.pending_aim=None;self.held=False;self.require_release=True
        for r in self.runtime.values():r.burst_remaining=0
    def resume(self):
        if self.phase=='paused':self.phase='active'
        self.clock.accumulator=0
    def clear_transients(self):
        self.missiles.clear();self.rockets.clear();self.lock.clear();self.pending_commands=[];self.held=False
        for r in self.runtime.values():r.cancel()
    def teardown(self):
        self.phase='teardown';self.clear_transients();self.aircraft.clear();self.enemies.clear();self.turrets.clear();self.events.clear();self.processed_hits.clear();self.clock.accumulator=0
    def metrics(self):
        return dict(entities=len(self.aircraft)+len(self.enemies)+len(self.turrets),missiles=len(self.missiles),rockets=len(self.rockets),locks=len(self.lock.progress),scheduled_callbacks=0,input_handlers=0)
    def snapshot(self):
        return dict(attempt_id=self.attempt_id,state_revision=self.revision,revision=self.revision,phase=self.phase,elapsed=self.elapsed,
            player=dict(position=self.player.position.tuple(),hp=self.player.hp,max_hp=self.player.max_hp,cooldowns=dict(self.player.cooldowns),ammo=self.player.rpg_ammo,aiming_factor=self.stats.aim_factor,armor_id=self.loadout.player.armor_id),
            weapon_slots=self.loadout.weapon_slots,active_weapon_id=self.active_weapon_id,weapon_runtime={k:asdict(v) for k,v in self.runtime.items()},city_hp=self.city.hp,
            aircraft=[dict(id=a.id,position=a.position.tuple(),hp=a.hp,max_hp=a.max_hp,status=a.status) for a in self.aircraft.values()],
            enemies=[dict(id=e.id,position=e.position.tuple(),hp=e.hp,max_hp=e.max_hp,phase=e.phase) for e in self.enemies.values()],
            turrets=[dict(id=t.id,turret_type_id=t.turret_type_id,position=t.position.tuple()) for t in self.turrets.values()],
            missiles=[dict(id=m.id,position=m.position.tuple()) for m in self.missiles.values()],rockets=[dict(id=r.id,position=r.position.tuple()) for r in self.rockets.values()],
            locks=dict(self.lock.progress),diagnostics=self.metrics(),events=deepcopy(self.events))

@dataclass
class PendingSave:
    candidate_profile: dict
    operation_id: str
    result: dict
    return_route: str
    continuation: object=None

class AppState:
    def __init__(self,repository=None):
        self.repository=repository or SlotRepository();self.screen='slot_select';self.slot=None;self.profile=None
        self.cursor=(1,1);self.battle=None;self.last_result=None;self.pending_save=None;self.error=None;self.settled=set();self.aim_mode='modern';self.draft=None

    def select_slot(self,slot):
        if self.pending_save:raise SaveError('pending_save','請先重試保存')
        self.profile=self.repository.load(slot) or self.repository.create(slot);self.slot=slot;self.cursor=(1,1);self.screen='profile_menu';self.last_result=None;self.draft=None

    def transaction(self,kind,operation_id=None,continuation=None,return_route=None,**fields):
        from .progression import transact
        if self.pending_save or self.profile is None:return {'result_code':'rejected','reason':'phase'}
        if kind in ('reward','failure'):
            b=self.battle
            if not b or b.phase!=('success' if kind=='reward' else 'failure') or operation_id!=b.attempt_id or fields!={'a':b.level.a,'b':b.level.b,'A':b.level.A}:
                return {'result_code':'rejected','reason':'phase'}
        elif kind=='confirm_loadout':
            if self.screen!='prepare_confirm':return {'result_code':'rejected','reason':'phase'}
        elif self.screen not in ('profile_menu','store','weapon_customize','rebirth_confirm'):
            return {'result_code':'rejected','reason':'phase'}
        operation_id=operation_id or uuid.uuid4().hex
        request=dict(kind=kind,profile_id=self.profile['profile_id'],rebirth_count=self.profile['rebirth_count'],**fields)
        candidate=deepcopy(self.profile);result=transact(candidate,operation_id,request)
        if candidate==self.profile:
            if result['result_code']=='applied' and continuation:continuation()
            return result
        route=return_route or self.screen
        self.profile=candidate
        try:self.repository.save(self.slot,candidate)
        except SaveError as exc:
            self.pending_save=PendingSave(deepcopy(candidate),operation_id,result,route,continuation);self.error=str(exc);self.screen='save_error'
            return {**result,'result_code':'failed_retryable','reason':'save_failed'}
        if continuation and result['result_code']=='applied':continuation()
        return result

    def begin_preparation(self):
        from .preparation import PreparationDraft
        if self.profile is None or self.pending_save or self.screen!='profile_menu':return None
        if self.battle:self.battle.teardown();self.battle=None
        self.draft=PreparationDraft.from_profile(self.profile);self.screen='prepare_armor';return self.draft

    def start(self,seed=1701):return self.begin_preparation()

    def set_draft_armor(self,armor_id):
        if not self.draft or self.pending_save:return 'phase'
        if armor_id is not None and armor_id not in self.profile['owned_armors']:return 'not_owned'
        self.draft.loadout['armor_id']=armor_id;return None

    def set_draft_slot(self,slot,weapon_id):
        if not self.draft or self.pending_save:return 'phase'
        if type(slot) is not int or not 1<=slot<=5:return 'invalid_slots'
        if weapon_id is not None and weapon_id not in self.profile['owned_weapons']:return 'not_owned'
        self.draft.loadout['weapon_slots'][slot-1]=weapon_id;return None

    def place_turret(self,instance_id,x,z):
        if not self.draft or self.pending_save:return 'phase'
        return self.draft.place(self.profile,instance_id,x,z)

    move_turret=place_turret
    def remove_turret(self,instance_id):
        if self.draft and not self.pending_save:self.draft.remove(instance_id)

    def next_preparation(self):
        from .preparation import STEPS
        if not self.draft or self.pending_save:return 'phase'
        if self.draft.step>=1:
            error=self.draft.validate(self.profile)
            if error:return error
        self.draft.step=min(3,self.draft.step+1);self.screen=STEPS[self.draft.step];return None

    def back_preparation(self):
        from .preparation import STEPS
        if not self.draft or self.pending_save:return
        if self.draft.step==0:self.cancel_preparation()
        else:self.draft.step-=1;self.screen=STEPS[self.draft.step]

    def cancel_preparation(self):
        if self.pending_save:return
        self.draft=None;self.screen='profile_menu'

    def confirm_and_start(self,seed=1701):
        from .loadout import resolve_loadout
        if not self.draft or self.pending_save or self.screen!='prepare_confirm':return None
        error=self.draft.validate(self.profile)
        if error:self.error=error;return None
        def saved():self.draft.revision=self.profile['profile_revision']
        result=self.transaction('confirm_loadout',loadout=self.draft.loadout,continuation=saved,return_route='prepare_confirm')
        if result['result_code']!='applied':return None
        snapshot=resolve_loadout(self.profile)
        self.battle=BattleState(self.profile,level_for(*self.cursor,2+self.profile['rebirth_count']),seed=seed,loadout_snapshot=snapshot)
        self.screen='battle';self.last_result=None;self.draft=None;return self.battle

    def settle(self):
        b=self.battle
        if self.pending_save or not b or b.phase not in ('success','failure') or b.attempt_id in self.settled:return
        self.settled.add(b.attempt_id);success=b.phase=='success';route='result_success' if success else 'result_failure'
        self.last_result=dict(success=success,reward=b.level.reward if success else 0,reason=b.failure_reason,level=b.level.level_id)
        def finished():
            self.cursor=next_level(b.level) if success else (b.level.a,b.level.b);self.screen=route
        self.transaction('reward' if success else 'failure',operation_id=b.attempt_id,continuation=finished,return_route=route,a=b.level.a,b=b.level.b,A=b.level.A)

    def purchase(self,key,operation_id=None):
        if self.pending_save or self.screen not in ('profile_menu','store','weapon_customize'):return 'phase'
        result=self.transaction('upgrade_player',operation_id,upgrade_id=key)
        return 'applied' if result['result_code']=='applied' else result['reason']

    def rebirth(self,operation_id=None):
        if self.pending_save or self.screen not in ('profile_menu','rebirth_confirm'):return 'phase'
        def finished():self.cursor=(1,1);self.screen='profile_menu';self.draft=None
        result=self.transaction('rebirth',operation_id,continuation=finished,return_route='profile_menu')
        return 'applied' if result['result_code']=='applied' else result['reason']

    def retry_save(self):
        pending=self.pending_save
        if not pending:return True
        try:self.repository.save(self.slot,pending.candidate_profile)
        except SaveError as exc:self.error=str(exc);return False
        self.profile=deepcopy(pending.candidate_profile);self.pending_save=None;self.error=None;self.screen=pending.return_route
        if pending.continuation and pending.result['result_code']=='applied':pending.continuation()
        return True

    def leave_battle(self):
        if self.pending_save:return
        if self.battle:self.battle.teardown();self.battle=None
        self.cursor=(1,1);self.screen='profile_menu'

    def show_menu(self):
        if self.pending_save:return
        if self.battle:self.battle.teardown();self.battle=None
        self.screen='profile_menu'

CampaignCursor=tuple[int,int]
