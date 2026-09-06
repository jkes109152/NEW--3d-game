"""鎖定、距離與攻擊驗證；視覺效果不持有傷害權限。"""
from dataclasses import dataclass, field
from math import ceil, radians, tan
from .entities import Aircraft, Enemy, V3, clamp, direction, ray_box, visible_between, world_boxes


@dataclass
class LockState:
    progress: dict[str,float] = field(default_factory=dict)
    valid: tuple[str,...] = ()
    current: str | None = None

    def clear(self):
        self.progress.clear()
        self.valid=()
        self.current=None

    def update(self, dt, candidates, alive, aiming, multi, duration):
        if not aiming:
            self.clear()
            return
        candidates=tuple(sorted(set(candidates)&set(alive)))
        if not multi:
            selected=self.current if self.current in candidates else (candidates[0] if candidates else self.current)
            if selected!=self.current:
                self.progress.clear()
                self.current=selected
            self.valid=(selected,) if selected in candidates else ()
        else:
            self.valid=candidates
        for key in list(self.progress):
            if key not in alive:
                del self.progress[key]
            elif key not in self.valid:
                self.progress[key]=max(0,self.progress[key]-dt/.75)
        for key in self.valid: self.progress[key]=min(1,self.progress.get(key,0)+dt/duration)

    def ready(self):
        return bool(self.valid) and all(self.progress.get(key,0)>=1-1e-9 for key in self.valid)


def target_in_box(player, position, size=.21, aspect=16/9, fov=90):
    """Ursina UI 的單位以視窗高度為準，對應水平視野。"""
    delta=position-player.eye
    forward=player.forward
    right=direction(player.yaw+90)
    up=V3(forward.y*right.z,forward.z*right.x-forward.x*right.z,-forward.y*right.x)
    depth=delta.dot(forward)
    if depth<=0: return False
    scale=aspect/(2*tan(radians(fov)/2)*depth)
    return abs(delta.dot(right)*scale)<=size/2+1e-9 and abs(delta.dot(up)*scale)<=size/2+1e-9


def ray_target(player, enemies):
    hits=[]
    for enemy in enemies.values():
        if enemy.hp<=0: continue
        distance=ray_box(player.eye,player.forward,*enemy.hit_envelope,180)
        if distance is not None: hits.append((distance,enemy.id))
    if not hits: return None,None
    distance,key=min(hits)
    for center,size in world_boxes():
        barrier=ray_box(player.eye,player.forward,center,size,distance)
        if barrier is not None and barrier<distance-1e-8: return None,None
    return key,distance


def can_fire(battle, runtime):
    if battle.phase!='active':return 'phase'
    error=runtime.error(battle.elapsed)
    if error:return error
    if battle.stats.category=='anti_air' and (not battle.player.aiming or not battle.lock.ready() or any(k not in battle.candidates() for k in battle.lock.valid)):return 'lock'
    return None


def turret_damage(enemy,damage=1):
    if enemy.kind=='GROUND_BOSS': return max(0,min(damage,enemy.hp-enemy.max_hp*.5))
    return min(damage,enemy.hp)


def aim_assist(profile, player, target, dt):
    if not player.aiming or not profile['owned_weapons']['W01']['upgrade_levels']['aim_assist'] or target is None: return (0,0)
    from .entities import angles
    yaw,pitch=angles(target.center-player.eye)
    dy=(yaw-player.yaw+180)%360-180
    dp=pitch-player.pitch
    length=(dy*dy+dp*dp)**.5
    factor=min(1,3*max(0,dt)/max(length,1e-9))
    return dy*factor,dp*factor
