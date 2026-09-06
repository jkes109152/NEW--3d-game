"""戰役、經濟與可重送的永久交易。"""
from dataclasses import dataclass
from math import floor
from copy import deepcopy
import hashlib
import json
from .config import WEAPONS

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

# 識別字、繁中名稱、基價、效果說明。
UPGRADES = (
    ('max_hp','強化生命',250,'最大生命 +10'),('armor','複合鎧甲',350,'每次受傷減少 1，至少承受 1'),
    ('aa_lock_time','導引演算',300,'防空鎖定時間 -0.15 秒'),('aa_whitebox','寬域雷達',250,'兩種防空白框 +10%'),
    ('aa_aim_assist','瞄準輔助',750,'開鏡時每秒最多修正 3°'),('weapon_cooldown','快速裝填',300,'全武器／砲塔冷卻 -5%'),
    ('rpg','RPG 火箭筒',500,'解鎖槽位 4；每關 3 發'),('auto_defense','陸地自動防禦',600,'每關部署 1 台砲塔'),
    ('auto_defense_capacity','砲塔容量',450,'額外部署 1 台，總數最多 6 台'),('multi_anti_aircraft','多目標防空炮',750,'解鎖槽位 5；全部鎖定後齊射'),
)
CATALOG={row[0]:row for row in UPGRADES}

def caps(r):
    return {'max_hp':5+r,'armor':3+r,'aa_lock_time':5+r,'aa_whitebox':5+r,'weapon_cooldown':5+r,'auto_defense_capacity':5}

def new_profile():
    return dict(schema_version=1,coins=0,rebirth_count=0,max_aircraft_count=2,upgrade_levels={},upgrade_caps=caps(0),
                unlocked_weapons=list(WEAPONS[:3]),rebirth_available=False,last_completed_a_b=None,profile_revision=0,operation_history=[])

def upgrade_level(p,key): return p['upgrade_levels'].get(key,0)
def cooldown_multiplier(p): return max(.50,1-.05*upgrade_level(p,'weapon_cooldown'))
def lock_time(p): return max(.1,3-.15*upgrade_level(p,'aa_lock_time'))
def price(p,key): return CATALOG[key][2]*(upgrade_level(p,key)+1)

def purchase_error(p,key):
    if key not in CATALOG: return 'invalid_id'
    if upgrade_level(p,key)>=caps(p['rebirth_count']).get(key,1): return 'maxed'
    if key=='auto_defense_capacity' and not upgrade_level(p,'auto_defense'): return 'prerequisite_missing'
    if p['coins']<price(p,key): return 'insufficient_coins'
    return None

def fingerprint(request):
    return hashlib.sha256(json.dumps(request,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')).hexdigest()

def validate_request(request):
    fields={'purchase':{'kind','upgrade_id'},'reward':{'kind','a','b','A'},
            'rebirth':{'kind'},'save':{'kind'},'failure':{'kind'}}
    kind=request.get('kind')
    if type(kind) is not str or kind not in fields or set(request)!=fields[kind]:
        raise ValueError('交易類型或欄位無效')
    if kind=='purchase' and type(request['upgrade_id']) is not str:
        raise ValueError('升級識別字必須是字串')
    if kind=='reward': roster_for(request['a'],request['b'],request['A'])

def transact(p,operation_id,request):
    if not isinstance(operation_id,str) or not operation_id: raise ValueError('操作 ID 不可為空')
    if type(request) is not dict: raise ValueError('交易要求必須是物件')
    fp=fingerprint(request)
    for op in p['operation_history']:
        if op['operation_id']==operation_id:
            return op['summary'].get('reason',op['result_code']) if op['request_fingerprint']==fp else 'operation_conflict'
    validate_request(request)
    result='applied'; kind=request.get('kind'); before=p['coins']; work=deepcopy(p)
    if kind=='purchase':
        key=request.get('upgrade_id'); result=purchase_error(work,key) or 'applied'
        if result=='applied':
            work['coins']-=price(work,key); work['upgrade_levels'][key]=upgrade_level(work,key)+1
            if key in ('rpg','multi_anti_aircraft'):
                work['unlocked_weapons'].append('RPG' if key=='rpg' else 'MULTI_ANTI_AIRCRAFT')
    elif kind=='rebirth':
        if not work['rebirth_available']: result='rebirth_unavailable'
        elif work['coins']<1000*(work['rebirth_count']+1): result='insufficient_coins'
        else:
            work['coins']=0; work['rebirth_count']+=1; work['max_aircraft_count']=2+work['rebirth_count']
            work['upgrade_caps']=caps(work['rebirth_count']); work['rebirth_available']=False
    elif kind=='reward':
        level=level_for(request['a'],request['b'],request['A'],work['rebirth_count'])
        if level.A!=work['max_aircraft_count']: return 'operation_conflict'
        else:
            work['coins']+=level.reward; work['last_completed_a_b']={'a':level.a,'b':level.b}
            work['rebirth_available'] |= level.is_final
    elif kind=='failure': work['rebirth_available']=True
    elif kind!='save': result='invalid_id'
    work['profile_revision']+=1
    stored_result='applied' if result=='applied' else 'operation_conflict' if result=='operation_conflict' else 'rejected'
    summary={'coins_delta':work['coins']-before,'reason':result}
    if kind=='purchase': summary['upgrade_id']=request.get('upgrade_id')
    work['operation_history'].append(dict(operation_id=operation_id,kind=kind,request_fingerprint=fp,result_code=stored_result,
          profile_revision=work['profile_revision'],summary=summary))
    p.clear(); p.update(work)
    return result
