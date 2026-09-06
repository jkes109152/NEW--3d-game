"""射線、掃掠與投射物來源快照。"""
from dataclasses import dataclass
from .entities import V3, ray_box
from .deployment import WORLD, visible

@dataclass(frozen=True)
class CollisionHit:
    distance:float
    point:V3
    normal:V3
    kind:str
    target_id:str | None=None

def _normal(point,center,size):
    distances=[]
    for i,(v,c,s) in enumerate(zip(point.tuple(),center.tuple(),size.tuple())):
        for sign in (-1,1):distances.append((abs(v-(c+sign*s/2)),i,sign))
    _,axis,sign=min(distances);v=[0,0,0];v[axis]=sign;return V3(*v)

def raycast_hit(origin,direction,max_distance,targets,world=None):
    world=world or WORLD;hits=[];ray=direction.normalized()
    boxes=list(world.boxes)
    left,right,bottom,top=world.bounds
    boxes.extend([(V3(left-.5,200,(top+bottom)/2),V3(1,400,top-bottom)),(V3(right+.5,200,(top+bottom)/2),V3(1,400,top-bottom)),(V3(0,200,bottom-.5),V3(right-left,400,1)),(V3(0,200,top+.5),V3(right-left,400,1))])
    for index,(center,size) in enumerate(boxes):
        d=ray_box(origin,ray,center,size,max_distance)
        if d is not None:
            point=origin+ray*d;hits.append((d,0,index,CollisionHit(d,point,_normal(point,center,size),'world')))
    if ray.y< -1e-12:
        d=(world.ground_y-origin.y)/ray.y
        if 0<=d<=max_distance+1e-9:hits.append((d,0,-1,CollisionHit(d,origin+ray*d,V3(0,1,0),'world')))
    for index,target in enumerate(targets):
        if target.hp<=0:continue
        d=ray_box(origin,ray,*target.hit_envelope,max_distance)
        if d is not None:hits.append((d,1,index,CollisionHit(d,origin+ray*d,_normal(origin+ray*d,*target.hit_envelope),'enemy',target.id)))
    if not hits:return None
    distance=min(x[0] for x in hits)
    return min((h for h in hits if h[0]<=distance+1e-9),key=lambda h:(h[1],h[2]))[3]

@dataclass
class Rocket:
    id:str
    weapon_id:str
    position:V3
    forward:V3
    speed:float
    remaining_range:float
    remaining_life:float
    damage:float
    blast_radius:float
    age:float=0
    def update(self,dt,targets):
        distance=min(self.remaining_range,self.speed*min(dt,self.remaining_life))
        hit=raycast_hit(self.position,self.forward,distance,targets)
        self.position=hit.point if hit else self.position+self.forward*distance
        self.remaining_range-=distance;self.remaining_life-=dt;self.age+=dt
        return hit,'hit' if hit else 'expired' if self.remaining_range<=1e-9 or self.remaining_life<=1e-9 else 'flying'

def explosion_targets(hit,radius,enemies):
    return [e for e in enemies if e.hp>0 and (e.center-hit.point).length()<=radius+1e-9 and visible(hit.point+hit.normal*.0001,e.center)]
