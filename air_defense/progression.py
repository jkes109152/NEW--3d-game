"""戰役、經濟與可重送的永久交易。"""
from dataclasses import dataclass
from math import floor
from copy import deepcopy
import hashlib
import json

@dataclass(frozen=True)
class LevelDefinition:
    a: int
    b: int
    A: int
    roster: tuple[str,...]
    reward: int
    is_final: bool

    @property
    def level_id(self): return f'{self.a}-{self.b}'

def roster_for(a,b,A):
    if any(type(n) is not int for n in (a,b,A)) or A<2 or not 1<=a<=A or not 1<=b<=(a+1 if a<A else 2*a+1):
        raise ValueError('無效的 a-b 戰役範圍')
    if b<=a+1: return ('NORMAL',)*(a-b+1)+('MANPOWER_SUPPORT',)*(b-1)
    return ('ARMORED_BOSS',)*(b-a-1)+('MANPOWER_SUPPORT',)*(2*a+1-b)

def level_for(a,b,A,r=None):
    roster=roster_for(a,b,A)
    r=A-2 if r is None else r
    return LevelDefinition(a,b,A,roster,floor((100+25*a+10*(b-1)+150*roster.count('ARMORED_BOSS'))*(1+.5*r)),a==A and b==2*a+1)

def campaign(A):
    if type(A) is not int or A<2: raise ValueError('戰役飛機上限必須是至少 2 的整數')
    for a in range(1,A+1):
        for b in range(1,(a+1 if a<A else 2*a+1)+1): yield level_for(a,b,A)

def next_level(level):
    if level.is_final: return (1,1)
    return (level.a,level.b+1) if level.b<(level.a+1 if level.a<level.A else 2*level.a+1) else (level.a+1,1)

from decimal import Decimal, ROUND_CEILING
from uuid import uuid4
import re
from .catalog import WEAPONS, FREE_WEAPONS, ARMORS, TURRETS, ATTACHMENTS, UPGRADE_PRICES, COLORS, PATTERNS, applicable_upgrade, upgrade_cap

from typing import TypedDict

class OwnedWeapon(TypedDict):
 upgrade_levels:dict[str,int]
 owned_attachments:list[str]
 selected_attachments:dict[str,str | None]
 owned_colors:list[str]
 selected_color:str
 owned_patterns:list[str]
 selected_pattern:str

class OwnedTurret(TypedDict):
 instance_id:str
 turret_id:str

class ProfileV2(TypedDict):
 schema_version:int
 profile_id:str
 coins:int
 rebirth_count:int
 profile_revision:int
 rebirth_available:bool
 last_completed_a_b:dict | None
 player_upgrades:dict[str,int]
 owned_weapons:dict[str,OwnedWeapon]
 owned_armors:list[str]
 owned_turrets:list[OwnedTurret]
 confirmed_loadout:dict
 operation_history:list[dict]

REQUEST_FIELDS = {
 'purchase_weapon':{'weapon_id'},'purchase_armor':{'armor_id'},'purchase_turret':{'turret_id'},
 'upgrade_player':{'upgrade_id'},'upgrade_weapon':{'weapon_id','upgrade_id'},
 'purchase_attachment':{'weapon_id','attachment_id'},'purchase_cosmetic':{'weapon_id','cosmetic_kind','cosmetic_id'},
 'customize_weapon':{'weapon_id','selected_attachments','selected_color','selected_pattern'},
 'confirm_loadout':{'loadout'},'reward':{'a','b','A'},'failure':{'a','b','A'},'coop_reward':{'a','b','A','party_size'},'rebirth':set()}

def valid_id(value):return type(value) is str and re.fullmatch('[0-9a-f]{32}',value) is not None

def new_weapon() -> OwnedWeapon:
 return dict(upgrade_levels={k:0 for k in UPGRADE_PRICES},owned_attachments=[],selected_attachments=dict(optic=None,barrel=None,feed=None),owned_colors=['original'],selected_color='original',owned_patterns=['plain'],selected_pattern='plain')

def new_profile(profile_id=None) -> ProfileV2:
 profile_id=profile_id or uuid4().hex
 if not valid_id(profile_id):raise ValueError('無效玩家識別')
 return dict(schema_version=2,profile_id=profile_id,coins=0,rebirth_count=0,profile_revision=0,rebirth_available=False,last_completed_a_b=None,player_upgrades={'max_hp':0},owned_weapons={k:new_weapon() for k in FREE_WEAPONS},owned_armors=[],owned_turrets=[],confirmed_loadout=dict(armor_id=None,weapon_slots=[*FREE_WEAPONS,None,None],deployments=[]),operation_history=[])

def fingerprint(request):
 return hashlib.sha256(json.dumps(request,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')).hexdigest()

def validate_request(req):
 if type(req) is not dict:raise ValueError('交易必須是物件')
 kind=req.get('kind')
 if type(kind) is not str or kind not in REQUEST_FIELDS or set(req)!=REQUEST_FIELDS[kind]|{'kind','profile_id','rebirth_count'}:raise ValueError('交易欄位無效')
 if not valid_id(req['profile_id']) or type(req['rebirth_count']) is not int or req['rebirth_count']<0:raise ValueError('交易身分無效')
 for key in REQUEST_FIELDS[kind]-{'a','b','A','party_size','loadout','selected_attachments'}:
  if type(req[key]) is not str:raise ValueError('交易識別字無效')
 if kind=='coop_reward':
  if type(req['party_size']) is not int or not 1<=req['party_size']<=4:raise ValueError('房間人數無效')
  roster_for(req['a'],req['b'],req['A'])
 if kind in ('reward','failure'):roster_for(req['a'],req['b'],req['A'])
 if kind=='confirm_loadout':
  load=req['loadout']
  if type(load) is not dict or set(load)!={'armor_id','weapon_slots','deployments'}:raise ValueError('配置欄位無效')
  if load['armor_id'] is not None and type(load['armor_id']) is not str:raise ValueError('裝甲型別無效')
  slots=load['weapon_slots']
  if type(slots) is not list or len(slots)!=5 or any(k is not None and type(k) is not str for k in slots):raise ValueError('槽位型別無效')
  if type(load['deployments']) is not list:raise ValueError('部署型別無效')
  for item in load['deployments']:
   if type(item) is not dict or set(item)!={'instance_id','x','z'} or type(item['instance_id']) is not str or any(type(item[k]) not in (float,int) for k in ('x','z')):raise ValueError('部署欄位無效')
 if kind=='customize_weapon':
  selected=req['selected_attachments']
  if type(selected) is not dict or set(selected)!={'optic','barrel','feed'} or any(k is not None and type(k) is not str for k in selected.values()):raise ValueError('配件型別無效')
 fingerprint(req)

class BusinessError(Exception):pass

def _apply(p,req,op):
 kind=req['kind'];summary={};cost=0
 def require(ok,reason):
  if not ok:raise BusinessError(reason)
 def buy(cost):require(p['coins']>=cost,'insufficient_coins');p['coins']-=cost
 if kind in ('purchase_weapon','purchase_armor'):
  weapon=kind=='purchase_weapon';field='weapon_id' if weapon else 'armor_id';key=req[field];catalog=WEAPONS if weapon else ARMORS;owned=p['owned_weapons'] if weapon else p['owned_armors']
  require(key in catalog,'invalid_id');require(key not in owned,'already_owned');buy(catalog[key].price)
  if weapon:owned[key]=new_weapon()
  else:owned.append(key);owned.sort()
  summary[field]=key
 elif kind=='purchase_turret':
  key=req['turret_id'];require(key in TURRETS,'invalid_id');require(p['rebirth_count']>=1,'locked');buy(TURRETS[key].price)
  instance='turret-'+op;p['owned_turrets'].append(dict(instance_id=instance,turret_id=key));summary.update(turret_id=key,instance_id=instance)
 elif kind in ('upgrade_player','upgrade_weapon'):
  key=req['upgrade_id'];weapon=kind=='upgrade_weapon'
  if weapon:
   wid=req['weapon_id'];require(wid in p['owned_weapons'],'not_owned');require(applicable_upgrade(wid,key),'incompatible');levels=p['owned_weapons'][wid]['upgrade_levels'];base=UPGRADE_PRICES[key];summary['weapon_id']=wid
  else:
   require(key=='max_hp','invalid_id');levels=p['player_upgrades'];base=250
  maximum=1 if key=='aim_assist' else upgrade_cap(p['rebirth_count']);require(levels[key]<maximum,'cap_reached');buy(base*(levels[key]+1));levels[key]+=1;summary.update(upgrade_id=key,new_level=levels[key])
 elif kind in ('purchase_attachment','purchase_cosmetic','customize_weapon'):
  wid=req['weapon_id'];require(wid in p['owned_weapons'],'not_owned');w=p['owned_weapons'][wid];summary['weapon_id']=wid
  if kind=='purchase_attachment':
   key=req['attachment_id'];require(key in ATTACHMENTS,'invalid_id');a=ATTACHMENTS[key];require(wid in a.applicable_weapons,'incompatible');require(key not in w['owned_attachments'],'already_owned');buy(a.price);w['owned_attachments'].append(key);w['owned_attachments'].sort();summary['attachment_id']=key
  elif kind=='purchase_cosmetic':
   ck=req['cosmetic_kind'];require(ck in ('color','pattern'),'invalid_id');key=req['cosmetic_id'];catalog=COLORS if ck=='color' else PATTERNS
   require(key in catalog,'invalid_id');owned=w['owned_colors' if ck=='color' else 'owned_patterns'];require(key not in owned,'already_owned');buy(75 if ck=='color' else 100);owned.append(key);owned.sort();summary.update(cosmetic_kind=ck,cosmetic_id=key)
  else:
   sel=req['selected_attachments'];require(set(sel)=={'optic','barrel','feed'},'incompatible')
   for slot,key in sel.items():require(key is None or type(key) is str and key in w['owned_attachments'] and ATTACHMENTS[key].slot==slot,'incompatible')
   require(req['selected_color'] in w['owned_colors'] and req['selected_pattern'] in w['owned_patterns'],'not_owned')
   for key in ('selected_attachments','selected_color','selected_pattern'):w[key]=deepcopy(req[key])
 elif kind=='confirm_loadout':
  from .loadout import validate_loadout
  reason=validate_loadout(p,req['loadout']);require(reason is None,reason);p['confirmed_loadout']=deepcopy(req['loadout']);summary['deployed_count']=len(req['loadout']['deployments'])
 elif kind=='coop_reward':
  require(req['A']<=p['rebirth_count']+2,'invalid_round');level=level_for(req['a'],req['b'],req['A'],p['rebirth_count'])
  reward=floor(level.reward*1.5**(req['party_size']-1));p['coins']+=reward
  summary.update(a=level.a,b=level.b,A=level.A,party_size=req['party_size'])
 elif kind in ('reward','failure'):
  require(req['A']==p['rebirth_count']+2,'invalid_round');level=level_for(req['a'],req['b'],req['A']);summary.update(a=level.a,b=level.b,A=level.A)
  if kind=='reward':p['coins']+=level.reward;p['last_completed_a_b']={'a':level.a,'b':level.b};p['rebirth_available']|=level.is_final
  else:p['rebirth_available']=True
 elif kind=='rebirth':
  require(p['rebirth_available'],'not_eligible');require(p['coins']>=1000*(p['rebirth_count']+1),'insufficient_coins')
  previous=p['rebirth_count'];fresh=new_profile(p['profile_id'])
  for key in ('operation_history','profile_revision','last_completed_a_b'):fresh[key]=p[key]
  fresh['rebirth_count']=previous+1;p.clear();p.update(fresh);summary.update(previous_rebirth_count=previous,new_rebirth_count=previous+1)
 return summary

def transact(p,operation_id,request):
 def result(code,reason,summary=None,replayed=False,revision=None):
  summary=deepcopy(summary or {'coins_delta':0})
  return dict(result_code=code,reason=reason,operation_id=operation_id,profile_revision=p['profile_revision'] if revision is None else revision,coins_delta=summary['coins_delta'],summary=summary,replayed=replayed)
 try:
  if not valid_id(operation_id):raise ValueError('操作識別字無效')
  validate_request(request)
 except (ValueError,TypeError,OverflowError):return result('rejected','invalid_request')
 if request['profile_id']!=p['profile_id']:return result('rejected','profile_mismatch')
 fp=fingerprint(request)
 for old in p['operation_history']:
  if old['operation_id']==operation_id:
   if old['request_fingerprint']!=fp:return result('operation_conflict','operation_conflict')
   return result(old['result_code'],old['reason'],old['summary'],True,old['profile_revision'])
 if request['rebirth_count']>p['rebirth_count']:return result('rejected','invalid_round')
 work=deepcopy(p);before=p['coins'];reason='ok';code='applied'
 try:
  if request['rebirth_count']<p['rebirth_count']:raise BusinessError('stale_round')
  summary=_apply(work,request,operation_id)
 except BusinessError as exc:work=deepcopy(p);reason=str(exc);code='rejected';summary={}
 summary['coins_delta']=work['coins']-before;work['profile_revision']+=1
 work['operation_history'].append(dict(operation_id=operation_id,kind=request['kind'],request_fingerprint=fp,result_code=code,reason=reason,profile_revision=work['profile_revision'],rebirth_count=request['rebirth_count'],summary=summary))
 from .save_data import validate_profile
 valid=validate_profile(work);p.clear();p.update(valid)
 return result(code,reason,summary)

@dataclass(frozen=True)
class DifficultySnapshot:
 a:int
 b:int
 air_hp_factor:Decimal
 ground_hp_factor:Decimal
 speed_factor:float
 turn_factor:float
 def hp(self,base,air=False):return int((Decimal(base)*(self.air_hp_factor if air else self.ground_hp_factor)).to_integral_value(rounding=ROUND_CEILING))

def difficulty_for(level):
 a,b=level.a,level.b;d=Decimal
 return DifficultySnapshot(a,b,min(d(4),1+d('.18')*(a-1)+d('.04')*(b-1)),min(d(4),1+d('.22')*(a-1)+d('.06')*(b-1)),float(min(d('1.35'),1+d('.035')*(a-1)+d('.01')*(b-1))),float(min(d('1.5'),1+d('.04')*(a-1)+d('.01')*(b-1))))

# 舊呈現適配入口於改造期間維持可匯入，數值仍取自 v2。
UPGRADES=(('max_hp','強化生命',250,'最大生命 +10'),)
CATALOG={r[0]:r for r in UPGRADES}
def caps(r):return {'max_hp':upgrade_cap(r)}
def upgrade_level(p,key):return p['player_upgrades'].get(key,0)
def cooldown_multiplier(p):return 1
def lock_time(p):return 3
def price(p,key):return 250*(upgrade_level(p,key)+1)
def purchase_error(p,key):return 'invalid_id' if key!='max_hp' else 'cap_reached' if upgrade_level(p,key)>=upgrade_cap(p['rebirth_count']) else 'insufficient_coins' if p['coins']<price(p,key) else None
