"""當局模擬與應用流程：狀態、時間、交易都有唯一來源。"""
from copy import deepcopy
from dataclasses import dataclass, replace
from math import cos, sin, tau
from random import Random
import uuid
from .config import AIR_START, MAX_STEPS, TICK, TURRET_POSITIONS, WEAPONS, COOLDOWNS
from .combat import LockState, aim_assist, ray_target, target_in_box, turret_damage, validate_attack
from .entities import Aircraft, City, Enemy, Missile, Player, Turret, V3, clamp, visible_between
from .progression import cooldown_multiplier, level_for, lock_time, next_level, upgrade_level
from .save_data import SaveError, SlotRepository


@dataclass(frozen=True)
class InputFrame:
    move_x: float = 0
    move_z: float = 0
    look_delta: tuple[float,float] = (0,0)
    jump_pressed: bool = False
    fire_pressed: bool = False
    aim_held: bool | None = None
    weapon_slot: int | None = None
    pause_requested: bool = False
    visible_aircraft: tuple[str,...] | None = None


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
    def __init__(self, profile, level, seed=1701, attempt_id=None, missile_factory=Missile):
        self.profile=deepcopy(profile)
        self.level=level
        self.attempt_id=attempt_id or uuid.uuid4().hex
        self.clock=SimulationClock()
        self.phase='active'
        self.elapsed=0.
        hp=100+10*upgrade_level(profile,'max_hp')
        self.player=Player(hp=hp,max_hp=hp,armor=upgrade_level(profile,'armor'))
        self.city=City()
        self.aircraft={}
        for index,kind in enumerate(level.roster):
            offset=(index-(len(level.roster)-1)/2)*10
            self.aircraft[f'air-{index}']=Aircraft(f'air-{index}',kind,V3(AIR_START[0]+offset,AIR_START[1],AIR_START[2]),formation_offset=offset)
        self.enemies={}
        self.turrets={}
        if upgrade_level(profile,'auto_defense'):
            count=1+upgrade_level(profile,'auto_defense_capacity')
            self.turrets={f'turret-{i}':Turret(f'turret-{i}',V3(*p)) for i,p in enumerate(TURRET_POSITIONS[:count])}
        self.missiles={}
        self.missile_factory=missile_factory
        self.lock=LockState()
        self.events=[]
        self.sequence=0
        self.revision=0
        self.failure_reason=None
        self.rng=Random(seed)
        self.drop_seeds={key:self.rng.getrandbits(64) for key in sorted(self.aircraft)}
        self.shot_number=0
        self.aspect=16/9
        self.fov=90
        self.last_error=None
        self.processed_hits=set()
        self.pending_frame=None

    def emit(self, kind, **payload):
        self.sequence+=1
        self.events.append(dict(kind=kind,attempt_id=self.attempt_id,sequence=self.sequence,**payload))

    def accept_event(self, event):
        return self.phase=='active' and event.get('attempt_id')==self.attempt_id

    def select_weapon(self, slot):
        if type(slot) is not int or not 1<=slot<=5 or WEAPONS[slot-1] not in self.profile['unlocked_weapons']:
            return 'weapon_locked'
        if self.player.weapon_slot!=slot:
            self.player.weapon_slot=slot
            self.player.aiming=False
            self.lock.clear()
        return 'applied'

    def toggle_aim(self):
        if self.player.weapon_slot in (1,2,5):
            self.player.aiming=not self.player.aiming
        if not self.player.aiming: self.lock.clear()

    def candidates(self, multiplier=1):
        size=.21*(1+.1*upgrade_level(self.profile,'aa_whitebox'))*(2 if self.player.weapon_slot==5 else 1)*multiplier
        return tuple(key for key,a in sorted(self.aircraft.items()) if a.hp>0 and a.status=='approaching'
                     and target_in_box(self.player,a.position,size,self.aspect,self.fov)
                     and visible_between(self.player.eye,a.position))

    def advance(self, dt, frame=None):
        self.events=[]
        if self.phase!='active': return self.snapshot()
        frame=frame or InputFrame()
        if frame.pause_requested:
            self.pause()
            return self.snapshot()
        count=self.clock.steps(dt)
        # 沒有固定步時保留離散輸入，不會吞掉高刷新率的按鍵。
        if count==0:
            previous=self.pending_frame or InputFrame()
            self.pending_frame=replace(frame,fire_pressed=frame.fire_pressed or previous.fire_pressed,
                jump_pressed=frame.jump_pressed or previous.jump_pressed,
                weapon_slot=frame.weapon_slot or previous.weapon_slot,
                aim_held=frame.aim_held if frame.aim_held is not None else previous.aim_held,
                look_delta=(frame.look_delta[0]+previous.look_delta[0],frame.look_delta[1]+previous.look_delta[1]))
            return self.snapshot()
        if self.pending_frame:
            pending=self.pending_frame
            frame=replace(frame,fire_pressed=frame.fire_pressed or pending.fire_pressed,
                jump_pressed=frame.jump_pressed or pending.jump_pressed,
                weapon_slot=frame.weapon_slot or pending.weapon_slot,
                aim_held=frame.aim_held if frame.aim_held is not None else pending.aim_held,
                look_delta=(frame.look_delta[0]+pending.look_delta[0],frame.look_delta[1]+pending.look_delta[1]))
            self.pending_frame=None
        for _ in range(count):
            self.step(TICK,frame)
            frame=replace(frame,jump_pressed=False,fire_pressed=False,weapon_slot=None,look_delta=(0,0))
            if self.phase!='active': break
        return self.snapshot()

    def step(self, dt, frame=None):
        if self.phase!='active' or dt<=0: return
        frame=frame or InputFrame()
        self.elapsed+=dt
        self.revision+=1
        self.processed_hits.clear()
        player=self.player
        if frame.weapon_slot is not None:
            error=self.select_weapon(frame.weapon_slot)
            if error!='applied': self.emit('error',code=error)
        player.yaw+=frame.look_delta[0]
        player.pitch=clamp(player.pitch+frame.look_delta[1],-85,85)
        if frame.aim_held is not None: player.aiming=frame.aim_held and player.weapon_slot in (1,2,5)
        player.tick(dt)
        player.move(clamp(frame.move_x,-1,1),clamp(frame.move_z,-1,1),frame.jump_pressed,dt)
        for aircraft in self.aircraft.values():
            aircraft.update(dt)
            if aircraft.status=='impact': self.fail('impact')
        if self.phase!='active': return
        for enemy in self.enemies.values(): enemy.update(dt,player)
        for key,missile in list(self.missiles.items()):
            result=missile.update(dt,self.aircraft.get(missile.target_id))
            if result=='hit':
                self.damage_aircraft(missile.target_id,1,missile.id)
            if result!='flying': self.missiles.pop(key,None)
        assist_ids=self.candidates(1.5)
        if assist_ids and player.weapon_slot in (1,5):
            yaw,pitch=aim_assist(self.profile,player,self.aircraft[assist_ids[0]],dt)
            player.yaw+=yaw
            player.pitch=clamp(player.pitch+pitch,-85,85)
        candidates=frame.visible_aircraft if frame.visible_aircraft is not None else self.candidates()
        alive={key for key,a in self.aircraft.items() if a.hp>0 and a.status=='approaching'}
        was_ready=self.lock.ready()
        self.lock.update(dt,candidates,alive,player.aiming and player.weapon_slot in (1,5),player.weapon_slot==5,lock_time(self.profile))
        if self.lock.ready() and not was_ready: self.emit('lock_complete')
        if frame.fire_pressed: self.fire()
        for turret in self.turrets.values():
            turret.cooldown=max(0,turret.cooldown-dt)
            target=self.enemies.get(turret.target_id)
            if target is None or not turret.legal(target):
                valid=[e for e in self.enemies.values() if turret.legal(e)]
                target=min(valid,key=lambda e:((e.center-turret.center).length(),e.id)) if valid else None
                turret.target_id=target.id if target else None
            if target and turret.cooldown<=1e-9:
                damage=turret_damage(target)
                if damage:
                    self.damage_enemy(target.id,damage,turret.id)
                    turret.cooldown=.2*cooldown_multiplier(self.profile)
                    self.emit('turret_fire',position=turret.center.tuple(),target=target.center.tuple())
        for enemy in list(self.enemies.values()):
            if enemy.hp<=0 or enemy.phase!='ground': continue
            if (enemy.position-self.city.position).horizontal().length()<=10:
                self.city.hp=max(0,self.city.hp-10*dt)
                if self.city.hp<=0:
                    self.fail('city')
                    break
            if enemy.cooldown<=1e-9 and (enemy.position-player.position).horizontal().length()<=38 \
                    and visible_between(enemy.center,player.eye):
                damage=player.hurt(8)
                enemy.cooldown=1.5
                self.emit('player_hurt',damage=damage,position=enemy.center.tuple())
                if player.hp<=0: self.fail('player')
            if self.phase!='active': break
        self.check_outcome()
        for key in sorted(list(self.enemies)):
            if self.enemies[key].hp<=0: del self.enemies[key]

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
            self.enemies[enemy_id]=Enemy(enemy_id,kind,pos,source_batch_id=aircraft.drop_batch_id,role=i%2)
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

    def fire(self, target_id=None, visible=True, ray_distance=None):
        player=self.player
        slot=player.weapon_slot
        if slot in (1,5):
            targets=tuple(self.lock.valid)
            target=self.aircraft.get(target_id or (targets[0] if targets else None))
        else:
            if target_id is None: target_id,ray_distance=ray_target(player,self.enemies)
            target=self.enemies.get(target_id) or self.aircraft.get(target_id)
            targets=(target_id,)
        error=validate_attack(self,target,visible,ray_distance)
        if error is None and slot==5:
            for key in targets:
                error=validate_attack(self,self.aircraft.get(key))
                if error: break
        if error:
            self.last_error=error
            self.emit('error',code=error)
            return error
        self.shot_number+=1
        shot=f'shot-{self.shot_number}'
        if slot in (1,5):
            if slot==1: targets=(target.id,)
            pending={}
            try:
                for index,key in enumerate(targets):
                    mid=f'{shot}-{index}'
                    pending[mid]=self.missile_factory(mid,key,player.eye,player.forward)
            except Exception:
                self.emit('error',code='launch_failed')
                return 'launch_failed'
            self.missiles.update(pending)
            self.lock.clear()
            self.emit('missile_launch',targets=targets,position=player.eye.tuple())
        elif slot==4:
            center=target.center
            for enemy in list(self.enemies.values()):
                if enemy.hp>0 and (enemy.center-center).length()<=6+1e-9: self.damage_enemy(enemy.id,35,shot)
            player.rpg_ammo-=1
            self.emit('explosion',position=center.tuple())
        else:
            self.damage_enemy(target.id,1,shot)
        player.cooldowns[slot]=COOLDOWNS[slot-1]*cooldown_multiplier(self.profile)
        self.emit('weapon_fire',weapon_slot=slot,position=player.eye.tuple(),target=target.center.tuple())
        self.last_error=None
        self.check_outcome()
        return 'applied'

    def fail(self, reason):
        if self.phase!='active': return
        self.phase='failure'
        self.failure_reason=reason
        self.emit('failure',reason=reason)

    def check_outcome(self):
        if self.phase!='active': return
        if self.player.hp<=0: self.fail('player')
        elif self.city.hp<=0: self.fail('city')
        elif all(a.status=='destroyed' for a in self.aircraft.values()) and all(e.hp<=0 for e in self.enemies.values()):
            self.phase='success'
            self.emit('success',reward=self.level.reward)

    def pause(self):
        if self.phase=='active': self.phase='paused'
        self.clock.accumulator=0
        self.pending_frame=None

    def resume(self):
        if self.phase=='paused': self.phase='active'
        self.clock.accumulator=0
        self.pending_frame=None

    def teardown(self):
        self.phase='teardown'
        self.aircraft.clear()
        self.enemies.clear()
        self.turrets.clear()
        self.missiles.clear()
        self.lock.clear()
        self.events.clear()
        self.processed_hits.clear()
        self.pending_frame=None
        self.clock.accumulator=0

    def metrics(self):
        return {'entities':len(self.aircraft)+len(self.enemies)+len(self.turrets),'missiles':len(self.missiles),
                'locks':len(self.lock.progress),'scheduled_callbacks':0,'input_handlers':0}

    def snapshot(self):
        return {'attempt_id':self.attempt_id,'state_revision':self.revision,'phase':self.phase,'elapsed':self.elapsed,
                'player':{'position':self.player.position.tuple(),'hp':self.player.hp,'max_hp':self.player.max_hp,
                          'cooldowns':dict(self.player.cooldowns),'ammo':self.player.rpg_ammo},
                'city_hp':self.city.hp,'aircraft':[{'id':a.id,'position':a.position.tuple(),'hp':a.hp,'status':a.status} for a in self.aircraft.values()],
                'enemies':[{'id':e.id,'position':e.position.tuple(),'hp':e.hp,'phase':e.phase} for e in self.enemies.values()],
                'locks':dict(self.lock.progress),'diagnostics':self.metrics(),'events':deepcopy(self.events)}


class AppState:
    def __init__(self, repository=None):
        self.repository=repository or SlotRepository()
        self.screen='slot_select'
        self.slot=None
        self.profile=None
        self.cursor=(1,1)
        self.battle=None
        self.last_result=None
        self.pending_save=False
        self.error=None
        self.settled=set()
        self.aim_mode='modern'

    def select_slot(self, slot):
        if self.pending_save: raise SaveError('pending_save','目前進度尚未保存，請先重試保存再切換紀錄。')
        self.profile=self.repository.load(slot) or self.repository.create(slot)
        self.slot=slot
        self.cursor=(1,1)
        self.screen='profile_menu'
        self.last_result=None

    def start(self, seed=1701):
        if self.profile is None or self.pending_save or self.screen!='profile_menu': return None
        if self.battle: self.battle.teardown()
        self.battle=BattleState(self.profile,level_for(*self.cursor,self.profile['max_aircraft_count']),seed=seed)
        self.screen='battle'
        self.last_result=None
        return self.battle

    def settle(self):
        battle=self.battle
        if not battle or battle.phase not in ('success','failure') or battle.attempt_id in self.settled: return
        self.settled.add(battle.attempt_id)
        success=battle.phase=='success'
        request={'kind':'reward','a':battle.level.a,'b':battle.level.b,'A':battle.level.A} if success else {'kind':'failure'}
        self.cursor=next_level(battle.level) if success else (1,1)
        self.last_result={'success':success,'reward':battle.level.reward if success else 0,'reason':battle.failure_reason,'level':battle.level.level_id}
        try:
            self.repository.transaction(self.slot,self.profile,battle.attempt_id,request)
        except SaveError as exc:
            self.pending_save=True
            self.error=str(exc)
        self.screen='result_success' if success else 'result_failure'

    def purchase(self, key, operation_id=None):
        if self.pending_save or self.screen not in ('profile_menu','store'): return 'phase'
        try:
            return self.repository.transaction(self.slot,self.profile,operation_id or uuid.uuid4().hex,{'kind':'purchase','upgrade_id':key})
        except SaveError as exc:
            self.pending_save=True
            self.error=str(exc)
            return 'save_failed'

    def rebirth(self, operation_id=None):
        if self.pending_save or self.screen not in ('profile_menu','rebirth_confirm'): return 'phase'
        try:
            result=self.repository.transaction(self.slot,self.profile,operation_id or uuid.uuid4().hex,{'kind':'rebirth'})
        except SaveError as exc:
            self.pending_save=True
            self.error=str(exc)
            result='save_failed'
        if result=='applied' or self.pending_save: self.cursor=(1,1)
        return result

    def retry_save(self):
        try: self.repository.save(self.slot,self.profile)
        except SaveError as exc:
            self.error=str(exc)
            return False
        self.pending_save=False
        self.error=None
        return True

    def leave_battle(self):
        if self.battle:
            self.battle.teardown()
            self.battle=None
        self.cursor=(1,1)
        self.screen='profile_menu'

    def show_menu(self):
        if self.battle:
            self.battle.teardown()
            self.battle=None
        self.screen='profile_menu'


CampaignCursor = tuple[int,int]
