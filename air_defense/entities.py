"""不依賴引擎的向量、碰撞包絡與戰鬥實體。"""
from dataclasses import dataclass, field
from math import acos, atan2, ceil, cos, degrees, pi, radians, sin, sqrt
from .config import AIRCRAFT, AIR_END, COVERS, PLAYER_SPAWN, ROUTE


@dataclass(frozen=True)
class V3:
    x: float = 0
    y: float = 0
    z: float = 0

    def __add__(self, other): return V3(self.x+other.x, self.y+other.y, self.z+other.z)
    def __sub__(self, other): return V3(self.x-other.x, self.y-other.y, self.z-other.z)
    def __mul__(self, value): return V3(self.x*value, self.y*value, self.z*value)
    def __truediv__(self, value): return self*(1/value)
    def dot(self, other): return self.x*other.x+self.y*other.y+self.z*other.z
    def length(self): return sqrt(self.dot(self))
    def normalized(self): return self/max(self.length(), 1e-12)
    def tuple(self): return (self.x, self.y, self.z)
    def horizontal(self): return V3(self.x, 0, self.z)


def clamp(value, low, high): return max(low, min(high, value))


def direction(yaw, pitch=0):
    y, p = radians(yaw), radians(pitch)
    return V3(sin(y)*cos(p), -sin(p), cos(y)*cos(p))


def angles(vector):
    return degrees(atan2(vector.x, vector.z)), -degrees(atan2(vector.y, max(vector.horizontal().length(), 1e-9)))


def approach_angle(current, target, limit):
    delta = (target-current+180) % 360-180
    return current+clamp(delta, -limit, limit)


def segment_distance(point, start, end):
    segment = end-start
    t = clamp((point-start).dot(segment)/max(segment.dot(segment), 1e-12), 0, 1)
    return (point-(start+segment*t)).length()


def ray_box(origin, ray, center, size, distance=1e6):
    """回傳射線碰到軸對齊包絡的距離；邊界包含在內。"""
    near, far = 0., distance
    for o, d, c, s in zip(origin.tuple(), ray.tuple(), center.tuple(), size.tuple()):
        lo, hi = c-s/2, c+s/2
        if abs(d)<1e-12:
            if o<lo or o>hi: return None
        else:
            a, b = (lo-o)/d, (hi-o)/d
            near, far = max(near,min(a,b)), min(far,max(a,b))
            if near>far+1e-9: return None
    return near


def world_boxes():
    return [(V3(x,y,z),V3(w,h,d)) for x,y,z,w,h,d in COVERS] + [(V3(0,10,-60),V3(18,20,14))]


def visible_between(start, end):
    delta=end-start
    length=delta.length()
    if length<1e-8: return True
    return not any(ray_box(start,delta/length,center,size,max(0,length-.01)) is not None
                   for center,size in world_boxes())


@dataclass
class Player:
    position: V3 = field(default_factory=lambda: V3(*PLAYER_SPAWN))
    hp: float = 100
    max_hp: float = 100
    armor: int = 0
    yaw: float = 0
    pitch: float = 0
    weapon_slot: int = 1
    cooldowns: dict = field(default_factory=lambda: {i:0. for i in range(1,6)})
    rpg_ammo: int = 3
    aiming: bool = False
    since_damage: float = 0
    healed: float = 0
    vertical_speed: float = 0

    @property
    def eye(self): return self.position+V3(0,1.6,0)
    @property
    def forward(self): return direction(self.yaw,self.pitch)

    def hurt(self, raw):
        if raw<=0 or self.hp<=0: return 0
        damage=min(self.hp,max(1,raw-self.armor))
        self.hp-=damage
        self.since_damage=0
        return damage

    def tick(self, dt):
        if dt<=0: return
        before=self.since_damage
        self.since_damage+=dt
        for key in self.cooldowns: self.cooldowns[key]=max(0,self.cooldowns[key]-dt)
        if self.hp>0:
            eligible=max(0,self.since_damage-5)-max(0,before-5)
            heal=max(0,min(eligible*2,self.max_hp-self.hp,self.max_hp*.2-self.healed))
            self.hp+=heal
            self.healed+=heal

    def move(self, x, z, jump, dt):
        movement=(direction(self.yaw)*z+direction(self.yaw+90)*x)
        if movement.length()>1: movement=movement.normalized()
        if jump and self.position.y<=1e-6: self.vertical_speed=sqrt(2*18*1.5)
        self.vertical_speed-=18*dt
        y=max(0,self.position.y+self.vertical_speed*dt)
        if y==0: self.vertical_speed=0
        pos=V3(self.position.x,y,self.position.z)
        for offset in (V3(movement.x*6*dt,0,0),V3(0,0,movement.z*6*dt)):
            candidate=pos+offset
            blocked=any(abs(candidate.x-c.x)<s.x/2+.45 and abs(candidate.z-c.z)<s.z/2+.45
                        and candidate.y<c.y+s.y/2 and candidate.y+1.8>c.y-s.y/2
                        for c,s in world_boxes())
            if not blocked: pos=candidate
        self.position=V3(clamp(pos.x,-59.55,59.55),pos.y,clamp(pos.z,-79.55,239.55))


@dataclass
class City:
    hp: float = 100
    position: V3 = field(default_factory=lambda: V3(0,0,-45))


@dataclass
class Aircraft:
    id: str
    kind: str
    position: V3
    hp: float | None = None
    elapsed: float = 0
    yaw: float = 180
    pitch: float = 4.6
    status: str = 'approaching'
    drop_batch_id: str | None = None
    formation_offset: float = 0

    def __post_init__(self):
        if self.hp is None: self.hp=AIRCRAFT[self.kind][0]

    @property
    def duration(self): return AIRCRAFT[self.kind][1]
    @property
    def remaining(self): return max(0,self.duration-self.elapsed)
    @property
    def center(self): return self.position

    def update(self, dt):
        if self.status!='approaching': return
        self.elapsed+=dt
        _, duration, amplitude, frequency, yaw_rate, pitch_rate, _ = AIRCRAFT[self.kind]
        t=clamp((self.elapsed+1.5)/duration,0,1)
        goal=V3(self.formation_offset*(1-t)+amplitude*sin(self.elapsed*frequency*2*pi)*sin(pi*t),
                32-22*t, 210-270*t)
        if t>=1: goal=V3(*AIR_END)
        target_yaw,target_pitch=angles(goal-self.position)
        self.yaw=approach_angle(self.yaw,target_yaw,yaw_rate*dt)
        self.pitch=approach_angle(self.pitch,target_pitch,pitch_rate*dt)
        speed=(V3(*AIR_END)-self.position).length()/max(self.remaining,1)
        old=self.position
        self.position+=direction(self.yaw,self.pitch)*speed*dt
        if segment_distance(V3(*AIR_END),old,self.position)<=10:
            self.status='impact'


@dataclass
class Enemy:
    id: str
    kind: str
    position: V3
    phase: str = 'descending'
    hp: float | None = None
    source_batch_id: str = ''
    descent_time: float = 0
    drop_height: float | None = None
    route_index: int = 0
    cooldown: float = 0
    age: float = 0
    yaw: float = 180
    role: int = 0

    def __post_init__(self):
        if self.hp is None: self.hp=self.max_hp
        if self.drop_height is None: self.drop_height=self.position.y

    @property
    def max_hp(self): return 10 if self.kind=='GROUND_BOSS' else 3
    @property
    def center(self): return self.position+V3(0,.9,0)
    @property
    def hit_envelope(self): return (self.center,V3(.8,1.8,.6))

    def update(self, dt, player):
        if self.hp<=0:
            self.phase='dead'
            return
        self.age+=dt
        self.cooldown=max(0,self.cooldown-dt)
        if self.phase=='descending':
            self.descent_time+=dt
            self.position=V3(self.position.x,self.drop_height*max(0,1-self.descent_time/4),self.position.z)
            if self.descent_time>=4-1e-9:
                self.phase='ground'
                self.position=V3(self.position.x,0,self.position.z)
            return
        goal=V3(*ROUTE[self.route_index])
        delta=goal-self.position
        if delta.length()<.15:
            self.route_index=min(len(ROUTE)-1,self.route_index+1)
            goal=V3(*ROUTE[self.route_index])
            delta=goal-self.position
        taking_cover=(int(self.age/2)+self.role)%2==0 and (player.position-self.position).horizontal().length()<38
        if taking_cover: return
        speed=2.5 if self.kind=='GROUND_BOSS' else 4
        step=delta.normalized()*min(speed*dt,delta.length())
        candidate=self.position+step
        if visible_between(self.center,candidate+V3(0,.9,0)):
            self.position=candidate
            if delta.length()>.01: self.yaw=angles(delta)[0]


@dataclass
class Turret:
    id: str
    position: V3
    target_id: str | None = None
    cooldown: float = 0

    @property
    def center(self): return self.position+V3(0,1,0)

    def legal(self, enemy):
        return enemy.hp>0 and enemy.phase=='ground' and (enemy.center-self.center).length()<=32+1e-9 \
            and visible_between(self.center,enemy.center) \
            and (enemy.kind!='GROUND_BOSS' or enemy.hp>ceil(enemy.max_hp*.5))


@dataclass
class Missile:
    id: str
    target_id: str
    position: V3
    forward: V3
    age: float = 0

    def update(self, dt, target):
        if target is None or target.hp<=0 or target.status!='approaching': return 'expired'
        desired=(target.position-self.position).normalized()
        current=self.forward.normalized()
        angle=acos(clamp(current.dot(desired),-1,1))
        step=min(angle,radians(240)*dt)
        if angle>1e-8:
            perpendicular=(desired-current*cos(angle)).normalized()
            if perpendicular.length()<.1: perpendicular=V3(current.z,0,-current.x).normalized()
            self.forward=(current*cos(step)+perpendicular*sin(step)).normalized()
        previous=self.position
        self.position+=self.forward*(90*dt)
        self.age+=dt
        if segment_distance(target.position,previous,self.position)<=1.5: return 'hit'
        return 'expired' if self.age>=5 else 'flying'


# 公開文件中的型別名稱對應同一份規則資料。
AircraftState, EnemyState, TurretState, MissileState = Aircraft, Enemy, Turret, Missile
PlayerState, CityState = Player, City
