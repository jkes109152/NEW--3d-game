"""不可變商品定義；數值承接 002 商品表。"""
from dataclasses import dataclass
from types import MappingProxyType

@dataclass(frozen=True)
class WeaponDefinition:
    id: str
    name: str
    category: str
    fire_mode: str
    price: int
    base_damage: float
    interval: float
    range: float
    magazine_size: int | None
    reload_seconds: float
    target_kind: str = 'enemy'
    delivery: str = 'hitscan'
    quota: int | None = None
    pellet_count: int = 1
    spread_angle: float = 0
    lock_seconds: float = 0
    lock_box_scale: float = 1
    projectile_speed: float = 0
    projectile_lifetime: float = 0
    blast_radius: float = 0
    aim_factor: float = 1.5

_ROWS = (
 ('W01','雲哨防空炮','anti_air','lock_single',0,1,1.25,240,None,0),
 ('W02','星群防空炮','anti_air','lock_multi',750,1,1.5,180,None,0),
 ('W03','糖粒手槍','pistol','semi',0,1,.2,24,12,1.3),
 ('W04','跳豆手槍','pistol','burst',300,.65,.08,28,18,1.5),
 ('W05','方糖重手槍','pistol','semi',450,2,.45,36,8,1.7),
 ('W06','薄荷步槍','rifle','auto',350,.6,.12,100,30,1.9),
 ('W07','果凍點放步槍','rifle','burst',450,.85,.09,120,24,2),
 ('W08','雪酥精準步槍','rifle','semi',550,1.5,.3,150,15,2),
 ('W09','焦糖重步槍','rifle','auto',650,1,.2,110,20,2.3),
 ('W10','彩虹輕步槍','rifle','auto',700,.45,.08,80,40,2.2),
 ('W11','汽泡衝鋒槍','smg','auto',250,.45,.075,36,24,1.4),
 ('W12','棉花糖衝鋒槍','smg','auto',350,.4,.06,30,32,1.8),
 ('W13','星糖點放衝鋒槍','smg','burst',400,.7,.07,45,27,1.6),
 ('W14','可可重衝鋒槍','smg','auto',500,.9,.15,42,20,1.7),
 ('W15','餅乾泵動霰彈槍','shotgun','bolt',400,.4,.9,18,6,2.6),
 ('W16','爆米花霰彈槍','shotgun','semi',650,.3,.4,15,8,2.8),
 ('W17','雲線狙擊槍','sniper','bolt',0,2,.75,180,5,2.4),
 ('W18','極光重狙擊槍','sniper','bolt',800,5,1.4,210,4,3),
 ('W19','彗星 RPG','rocket','semi',500,35,2.5,60,1,2.5),
 ('W20','流星輕火箭','rocket','semi',850,22,1.6,90,1,1.6),
)
def _weapon(row):
    kind=row[2];extra={}
    if kind=='anti_air':extra=dict(target_kind='aircraft',delivery='homing',lock_seconds=3,lock_box_scale=2 if row[0]=='W02' else 1,projectile_speed=90,projectile_lifetime=5,aim_factor=1)
    if kind=='rocket':extra=dict(delivery='rocket',quota=3 if row[0]=='W19' else 5,projectile_speed=45 if row[0]=='W19' else 60,projectile_lifetime=3,blast_radius=6 if row[0]=='W19' else 4,aim_factor=1.25)
    if kind=='shotgun':extra=dict(pellet_count=8,spread_angle=3.5)
    if kind=='sniper':extra=dict(aim_factor=4)
    return WeaponDefinition(*row,**extra)
WEAPONS=MappingProxyType({r[0]:_weapon(r) for r in _ROWS})
FREE_WEAPONS=('W01','W17','W03')
CATEGORY_NAMES=MappingProxyType(dict(anti_air='防空',pistol='手槍',rifle='步槍',smg='衝鋒槍',shotgun='霰彈槍',sniper='狙擊槍',rocket='火箭'))
MODE_NAMES=MappingProxyType(dict(semi='半自動',auto='全自動',burst='三連發',bolt='手動上膛',lock_single='單目標鎖定',lock_multi='多目標鎖定'))

@dataclass(frozen=True)
class ArmorDefinition:
    id: str
    name: str
    price: int
    hp_delta: int
    speed_factor: float
    damage_reduction: int
    regen_delay: float
    regen_rate: float

ARMORS=MappingProxyType({r[0]:ArmorDefinition(*r) for r in (
 ('A01','棉雲裝甲',400,0,1,0,5,4),('A02','糖晶裝甲',450,0,.9,3,5,2),
 ('A03','果凍裝甲',400,10,1,1,5,3),('A04','輕羽裝甲',350,-10,1.2,0,5,2),
 ('A05','蜜糖裝甲',500,40,.95,0,5,2),('A06','晨露裝甲',400,0,1,0,2.5,2))})

@dataclass(frozen=True)
class TurretDefinition:
    id: str
    name: str
    price: int
    target_kind: str
    damage: float
    interval: float
    range: float
    lock_seconds: float=0
TURRETS=MappingProxyType({r[0]:TurretDefinition(*r) for r in (
 ('T01','糖粒機槍塔',600,'enemy',1,.2,32),('T02','雲眼狙擊塔',900,'enemy',3,1.5,70),('T03','星哨防空塔',1200,'aircraft',1,2,180,1))})

@dataclass(frozen=True)
class AttachmentDefinition:
    id: str
    name: str
    slot: str
    price: int
    applicable_weapons: tuple
    multipliers: tuple

GROUND=tuple(f'W{i:02}' for i in range(3,19))
GUIDED=('W01','W02','W19','W20')
ATTACHMENTS=MappingProxyType({r[0]:AttachmentDefinition(*r) for r in (
 ('zoom_scope','放大鏡','optic',150,GROUND,(('aim_factor',1.5),('reload_seconds',1.1))),
 ('guidance_scope','導引鏡','optic',150,GUIDED,()),
 ('heavy_barrel','重型組件','barrel',200,tuple(WEAPONS),(('base_damage',1.15),('interval',1.1),('burst_interval',1.1))),
 ('extended_magazine','擴充彈匣','feed',150,GROUND,(('magazine_size',1.5),('reload_seconds',1.2))),
 ('quick_reload','快速裝填','feed',150,GROUND,(('magazine_size',.8),('reload_seconds',.8))),
 ('cooling_guidance','散熱導引器','feed',200,('W01','W02'),(('interval',.85),('lock_seconds',1.15))),
 ('light_loading_rack','輕量裝填架','feed',200,('W19','W20'),(('interval',.85),('reload_seconds',.85),('blast_radius',.85))) )})
UPGRADE_PRICES=MappingProxyType(dict(damage=200,cooldown=300,range=200,lock_time=300,whitebox=250,aim_assist=750))
UPGRADE_NAMES=MappingProxyType(dict(damage='傷害強化',cooldown='射擊節奏',range='精準射程',lock_time='鎖定演算',whitebox='雷達白框',aim_assist='瞄準輔助'))
COLORS=MappingProxyType(dict(original='原色',mint='薄荷青',strawberry='草莓粉',lemon='檸檬黃',grape='葡萄紫'))
PATTERNS=MappingProxyType(dict(plain='素面',dots='糖粒圓點',stripes='糖果條紋',stars='星星'))
def upgrade_cap(r):return min(10,5+r)
def applicable_upgrade(weapon_id,key):
    return key in ('damage','cooldown') or key=='range' and weapon_id in ('W17','W18') or key in ('lock_time','whitebox','aim_assist') and weapon_id in ('W01','W02')
