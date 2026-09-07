"""合作戰鬥：房主模擬一份世界，每人各有武器、生命與鎖定狀態。"""
from dataclasses import replace
from math import ceil, floor
from .state import BattleState, InputFrame
from .entities import V3
from .config import TICK


def party_multiplier(count):
    if type(count) is not int or not 1 <= count <= 4:
        raise ValueError('房間人數必須為一至四人')
    return 1.5 ** (count - 1)


def party_level(level, count):
    factor = party_multiplier(count)
    total = ceil(len(level.roster) * factor)
    roster = tuple(level.roster[i % len(level.roster)] for i in range(total))
    return replace(level, roster=roster, reward=floor(level.reward * factor))


class CooperativeBattle(BattleState):
    def __init__(self, members, level, run_id):
        if not members: raise ValueError('房間沒有玩家')
        scaled = party_level(level, len(members))
        super().__init__(members[0]['profile'], scaled, attempt_id=run_id)
        self.member_id = members[0]['id']
        self.names = {m['id']: m['name'] for m in members}
        self.actors = {self.member_id: self}
        self.pending_frames = {}
        self.count = len(members)
        # Formation remains in the playable corridor even with larger parties.
        for i, aircraft in enumerate(self.aircraft.values()):
            offset=(i-(len(self.aircraft)-1)/2)*min(10,90/max(1,len(self.aircraft)-1))
            aircraft.formation_offset=offset
            aircraft.position=V3(offset,aircraft.position.y,aircraft.position.z)
        for i,m in enumerate(members[1:],1):
            actor=BattleState(m['profile'], scaled, attempt_id=run_id+'-'+m['id'])
            actor.player.position=V3(-18+i*3,0,70)
            for key in ('aircraft','enemies','missiles','rockets','city','drop_seeds','processed_hits'):
                setattr(actor,key,getattr(self,key))
            actor.emit=lambda kind, _id=m['id'], **payload: self.emit(kind,player_id=_id,**payload)
            for key,turret in actor.turrets.items():self.turrets[m['id']+':'+key]=turret
            actor.turrets=self.turrets
            self.actors[m['id']]=actor

    def combat_players(self):
        return [a.player for a in self.actors.values()] if hasattr(self,'actors') else [self.player]

    def queue(self, member, frame):
        if member not in self.actors:return
        previous=self.pending_frames.get(member,InputFrame())
        self.pending_frames[member]=replace(frame,
            commands=(*previous.commands,*frame.commands)[-96:],
            look_delta=tuple(a+b for a,b in zip(previous.look_delta,frame.look_delta)))

    def advance_group(self, dt, frames):
        self.events=[]
        if self.phase!='active':return
        for member,frame in frames.items():self.queue(member,frame)
        count=self.clock.steps(dt)
        for i in range(count):
            self.elapsed+=TICK;self.revision+=1;self.processed_hits.clear()
            current=dict(self.pending_frames)
            for member,actor in self.actors.items():
                actor.elapsed=self.elapsed;actor.revision=self.revision
                frame=current.get(member,InputFrame())
                if actor.player.hp>0:actor.move_player(TICK,frame)
            self.step_world(TICK)
            if self.phase!='active':break
            for member,actor in self.actors.items():
                frame=current.get(member,InputFrame())
                if actor.player.hp>0:actor.step_weapon(TICK,frame)
                else:actor.lock.clear();actor.held=False
                self.pending_frames[member]=replace(frame,commands=(),look_delta=(0,0),jump_pressed=False,fire_pressed=False,weapon_slot=None)
                actor.finish_player()
            self.step_projectiles(TICK)
            self.check_outcome()
            for key in list(self.enemies):
                if self.enemies[key].hp<=0:del self.enemies[key]
            if self.phase!='active':break
        for actor in self.actors.values():actor.phase=self.phase

    def roster_snapshot(self):
        return [dict(id=key,name=self.names[key],position=a.player.position.tuple(),yaw=a.player.yaw,
                     hp=a.player.hp,max_hp=a.player.max_hp,weapon_id=a.active_weapon_id)
                for key,a in self.actors.items()]
