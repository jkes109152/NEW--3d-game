"""鎖定、距離與攻擊驗證；視覺效果不持有傷害權限。"""
from dataclasses import dataclass, field
from math import ceil, radians, tan
from .config import WEAPONS, RANGES, COOLDOWNS
from .entities import Aircraft, Enemy, V3, clamp, direction, ray_box, visible_between, world_boxes
from .progression import cooldown_multiplier, upgrade_level


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


def validate_attack(battle, target, visible=True, ray_distance=None):
    player=battle.player
    slot=player.weapon_slot
    if WEAPONS[slot-1] not in battle.profile['unlocked_weapons']: return 'weapon_locked'
    if battle.phase!='active': return 'phase'
    if target is None or (slot in (1,5))!=isinstance(target,Aircraft): return 'target_type'
    if target.hp<=0: return 'dead'
    # 地面武器使用實際射線交點；人物中心被掩體遮住時，露出的頭部仍可命中。
    hit_point=player.eye+player.forward*ray_distance if slot not in (1,5) and ray_distance is not None else target.center
    if not visible or not visible_between(player.eye,hit_point): return 'blocked'
    distance=(target.center-player.position).horizontal().length() if slot==5 else \
        (ray_distance if ray_distance is not None else (target.center-player.eye).length())
    if distance>RANGES[slot-1]+1e-9: return 'range'
    if player.cooldowns[slot]>1e-9: return 'cooldown'
    if slot==4 and player.rpg_ammo<=0: return 'ammo'
    if slot in (1,5) and (not player.aiming or not battle.lock.ready() or target.id not in battle.lock.valid): return 'lock'
    return None


def turret_damage(enemy):
    if enemy.kind=='GROUND_BOSS': return max(0,min(1,enemy.hp-ceil(enemy.max_hp*.5)))
    return min(1,enemy.hp)


def aim_assist(profile, player, target, dt):
    if not player.aiming or not upgrade_level(profile,'aa_aim_assist') or target is None: return (0,0)
    from .entities import angles
    yaw,pitch=angles(target.center-player.eye)
    dy=(yaw-player.yaw+180)%360-180
    dp=pitch-player.pitch
    length=(dy*dy+dp*dp)**.5
    factor=min(1,3*max(0,dt)/max(length,1e-9))
    return dy*factor,dp*factor
