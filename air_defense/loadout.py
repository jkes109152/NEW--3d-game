"""以商品與所有權解析不可變的當局能力及配置。"""
from dataclasses import dataclass, asdict
from decimal import Decimal
from types import MappingProxyType
from .catalog import WEAPONS, ARMORS, ATTACHMENTS

@dataclass(frozen=True)
class EffectiveWeaponStats:
    weapon_id: str
    definition: object
    values: object
    attachment_ids: tuple
    color_id: str
    pattern_id: str
    def __getattr__(self,key):
        values=object.__getattribute__(self,'values')
        if key in values:return values[key]
        return getattr(object.__getattribute__(self,'definition'),key)

@dataclass(frozen=True)
class EffectivePlayerStats:
    max_hp: float
    move_speed: float
    jump_height: float
    damage_reduction: float
    regen_delay: float
    regen_rate: float
    regen_budget: float
    armor_id: str | None

def resolve_weapon_stats(profile,weapon_id):
    w=WEAPONS[weapon_id];owned=profile['owned_weapons'][weapon_id];levels=owned['upgrade_levels']
    d=lambda n:Decimal(str(n))
    values={k:d(v) for k,v in asdict(w).items() if type(v) in (float,int) and k not in ('price','quota','pellet_count')}
    values['base_damage']*=1+d('.25')*levels['damage']
    values['range']+=30*levels['range']
    tempo=max(d('.5'),1-d('.05')*levels['cooldown'])
    values['interval']*=tempo;values['burst_interval']=d('.45')*tempo
    if w.category=='anti_air':
        values['lock_seconds']=max(d('1.5'),3-d('.15')*levels['lock_time'])
        values['lock_box_scale']*=1+d('.1')*levels['whitebox']
    selected=tuple(x for x in owned['selected_attachments'].values() if x)
    for key in selected:
        a=ATTACHMENTS[key]
        modifiers=a.multipliers
        if key=='guidance_scope':modifiers=(('lock_box_scale',1.1),('lock_seconds',1.1)) if w.category=='anti_air' else (('aim_factor',1.5),('reload_seconds',1.1))
        for field,multiplier in modifiers:values[field]*=d(multiplier)
    values={k:float(v) for k,v in values.items()}
    values['magazine_size']=max(1,int(values['magazine_size'])) if w.magazine_size else None
    values['aim_assist']=bool(levels['aim_assist'])
    return EffectiveWeaponStats(weapon_id,w,MappingProxyType(values),selected,owned['selected_color'],owned['selected_pattern'])

def resolve_player_stats(profile,armor_id=None):
    a=ARMORS.get(armor_id)
    hp=100+10*profile['player_upgrades']['max_hp']+(a.hp_delta if a else 0)
    return EffectivePlayerStats(hp,6*(a.speed_factor if a else 1),1.8,a.damage_reduction if a else 0,a.regen_delay if a else 5,a.regen_rate if a else 2,hp*.2,armor_id)

def validate_loadout(profile,loadout,world=None):
    from .deployment import validate_deployment
    if type(loadout) is not dict or set(loadout)!={'armor_id','weapon_slots','deployments'}:return 'invalid_loadout'
    armor=loadout['armor_id']
    if armor is not None and (type(armor) is not str or armor not in profile['owned_armors']):return 'not_owned'
    slots=loadout['weapon_slots']
    if type(slots) is not list or len(slots)!=5:return 'invalid_slots'
    owned=[]
    for key in slots:
        if key is None:continue
        if type(key) is not str or key not in profile['owned_weapons']:return 'not_owned'
        if key in owned:return 'duplicate_weapon'
        owned.append(key)
    if not any(WEAPONS[k].category=='anti_air' for k in owned) or not any(WEAPONS[k].category!='anti_air' for k in owned):return 'missing_target_kind'
    return validate_deployment(profile,loadout['deployments'],world)

@dataclass(frozen=True)
class BattleLoadout:
    weapon_slots: tuple
    weapons: object
    player: EffectivePlayerStats
    deployments: tuple

def resolve_loadout(profile,loadout=None):
    from .catalog import TURRETS
    loadout=profile['confirmed_loadout'] if loadout is None else loadout
    reason=validate_loadout(profile,loadout)
    if reason:raise ValueError(reason)
    types={t['instance_id']:t['turret_id'] for t in profile['owned_turrets']}
    return BattleLoadout(tuple(loadout['weapon_slots']),MappingProxyType({k:resolve_weapon_stats(profile,k) for k in loadout['weapon_slots'] if k}),
        resolve_player_stats(profile,loadout['armor_id']),tuple((d['instance_id'],TURRETS[types[d['instance_id']]],d['x'],d['z']) for d in sorted(loadout['deployments'],key=lambda x:x['instance_id'])))
