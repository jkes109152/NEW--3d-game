"""部署幾何和世界可見性，與引擎無關。"""
from dataclasses import dataclass, field
from math import isfinite, sin, cos, tau
from .config import PLAYER_SPAWN, ROUTE
from .entities import V3, ray_box, segment_distance, world_boxes

@dataclass(frozen=True)
class WorldDefinition:
    bounds: tuple=(-60,60,-80,240)
    ground_y: float=0
    player_spawn: V3=field(default_factory=lambda:V3(*PLAYER_SPAWN))
    boxes: tuple=field(default_factory=lambda:tuple(world_boxes()))
    enemy_route: tuple=field(default_factory=lambda:tuple(V3(*p) for p in ROUTE))

WORLD=WorldDefinition()

def visible(start,end,world=None):
    world=world or WORLD;delta=end-start;length=delta.length()
    return length<1e-9 or all(ray_box(start,delta/length,c,size,max(0,length-1e-7)) is None for c,size in world.boxes)

def validate_placement(world,position,others=()):
    world=world or WORLD
    if len(position)!=2 or any(type(v) not in (int,float) or not isfinite(v) for v in position):return 'invalid_position'
    x,z=position;left,right,bottom,top=world.bounds;r=1.5
    if not left+r-1e-9<=x<=right-r+1e-9 or not bottom+r-1e-9<=z<=top-r+1e-9:return 'outside_map'
    for center,size in world.boxes:
        dx=max(abs(x-center.x)-size.x/2,0);dz=max(abs(z-center.z)-size.z/2,0)
        if dx*dx+dz*dz<=r*r+1e-9:return 'blocked_ground'
    pos=V3(x,0,z)
    if (pos-world.player_spawn.horizontal()).length()<=4.5+1e-9:return 'spawn_reserved'
    if any(segment_distance(pos,a.horizontal(),b.horizontal())<=3.5+1e-9 for a,b in zip(world.enemy_route,world.enemy_route[1:])):return 'route_reserved'
    if any((pos-V3(o['x'],0,o['z'])).length()<3-1e-9 for o in others):return 'overlap'
    return None

def validate_deployment(profile,placements,world=None):
    if type(placements) is not list:return 'invalid_position'
    if len(placements)>2*profile['rebirth_count']:return 'capacity'
    ids={t['instance_id'] for t in profile['owned_turrets']};seen=set();valid=[]
    for p in placements:
        if type(p) is not dict or set(p)!={'instance_id','x','z'}:return 'invalid_position'
        key=p['instance_id']
        if type(key) is not str or key not in ids:return 'not_owned'
        if key in seen:return 'duplicate_instance'
        error=validate_placement(world,(p['x'],p['z']),valid)
        if error:return error
        seen.add(key);valid.append(p)
    return None

def range_preview(position,radius,world=None):
    origin=V3(position[0],1.2,position[1])
    return tuple((origin.x+cos(i*tau/72)*radius*j/16,origin.z+sin(i*tau/72)*radius*j/16,
        visible(origin,V3(origin.x+cos(i*tau/72)*radius*j/16,.95,origin.z+sin(i*tau/72)*radius*j/16),world)) for i in range(72) for j in range(1,17))
