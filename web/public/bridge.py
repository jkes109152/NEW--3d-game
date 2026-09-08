"""瀏覽器適配層；戰役與交易沿用桌面版純規則。"""
import json
from datetime import datetime, timezone
from time import monotonic
from uuid import uuid4
from dataclasses import asdict
from air_defense.state import AppState, InputFrame
from air_defense.weapons import InputCommand
from air_defense.save_data import SaveError, validate_profile
from air_defense.progression import new_profile
from air_defense.catalog import *
from air_defense.config import ERRORS, COVERS, ROUTE
from air_defense.visual_catalog import RECIPES, PALETTE, ARMOR_PARTS
from air_defense.combat import can_fire
from air_defense.loadout import resolve_weapon_stats,resolve_player_stats
from air_defense.progression import new_weapon

class BrowserRepository:
    def __init__(self, storage):
        self.storage = storage
        self.delete_tokens = {}
        self.last_touch = {}
    def key(self, slot):
        if type(slot) is not int or not 1 <= slot <= 5: raise ValueError('無效欄位')
        return f'candy-defense-web-v2:slot-{slot}'
    def raw(self, slot):
        try: raw = self.storage.getItem(self.key(slot))
        except Exception as e: raise SaveError('read_failed','瀏覽器拒絕讀取存檔') from e
        if raw is None or type(raw).__name__ == 'JsNull': return None
        return str(raw)
    def decode(self, raw):
        data = json.loads(raw)
        # Keep the original closed profile schema; browser metadata shares its atomic storage entry.
        if type(data) is dict and data.get('format') == 'candy-defense-slot-v1':
            return validate_profile(data['profile']), data.get('last_played_at')
        return validate_profile(data), None
    def load(self, slot):
        raw = self.raw(slot)
        if raw is None: return None
        try: return self.decode(raw)[0]
        except Exception as e: raise SaveError('corrupt','存檔損壞或版本不支援；原始資料已保留，請選擇其他欄位。') from e
    def save(self, slot, profile):
        try:
            data = dict(format='candy-defense-slot-v1', profile=validate_profile(profile), last_played_at=datetime.now(timezone.utc).isoformat())
            self.storage.setItem(self.key(slot), json.dumps(data,ensure_ascii=False,allow_nan=False))
            self.last_touch[slot] = monotonic()
        except Exception as e: raise SaveError('write_failed','瀏覽器保存失敗，請釋放空間後重試保存。') from e
    def create(self, slot):
        p=new_profile();self.save(slot,p);return p
    def touch(self, slot, force=False):
        if not force and monotonic()-self.last_touch.get(slot,0)<30: return
        profile = self.load(slot)
        if profile is not None: self.save(slot,profile)
    def list_slots(self):
        rows=[]
        for slot in range(1,6):
            row=dict(slot=slot,status='empty',last_played_at=None)
            try:
                raw=self.raw(slot)
                if raw is not None:
                    row['status']='corrupt'
                    profile,stamp=self.decode(raw)
                    row.update(status='ready',last_played_at=stamp,coins=profile['coins'],rebirth_count=profile['rebirth_count'])
            except SaveError: row['status']='unavailable'
            except Exception: pass
            rows.append(row)
        return rows
    def request_delete(self,slot):
        raw=self.raw(slot)
        if raw is None: raise SaveError('empty','此欄位沒有存檔。')
        token=uuid4().hex
        self.delete_tokens[token]=(slot,raw)
        return dict(slot=slot,token=token)
    def cancel_delete(self,token): self.delete_tokens.pop(token,None)
    def confirm_delete(self,slot,token):
        expected=self.delete_tokens.pop(token,None)
        if expected is None or expected[0]!=slot: raise SaveError('confirmation','請重新確認要刪除的存檔。')
        self.delete_tokens={k:v for k,v in self.delete_tokens.items() if v[0]!=slot}
        if self.raw(slot)!=expected[1]: raise SaveError('changed','存檔已變更，資料已保留。請重新選擇並確認刪除。')
        try: self.storage.removeItem(self.key(slot))
        except Exception as e: raise SaveError('delete_failed','刪除未完成，請稍後重試；存檔仍保留。') from e
        self.last_touch.pop(slot,None)

def initialize(storage):
    global app,ui_generation,ui_route,delete_confirmation
    app=AppState(BrowserRepository(storage))
    ui_generation=0;ui_route=None
    delete_confirmation=None

def catalog_json():
    return json.dumps(dict(weapons={k:asdict(v) for k,v in WEAPONS.items()},armors={k:asdict(v) for k,v in ARMORS.items()},turrets={k:asdict(v) for k,v in TURRETS.items()},attachments={k:asdict(v) for k,v in ATTACHMENTS.items()},upgrades=dict(UPGRADE_PRICES),upgrade_names=dict(UPGRADE_NAMES),colors=dict(COLORS),patterns=dict(PATTERNS),categories=dict(CATEGORY_NAMES),modes=dict(MODE_NAMES),recipes=dict(RECIPES),palette=dict(PALETTE),armor_parts=dict(ARMOR_PARTS),covers=COVERS,route=ROUTE),ensure_ascii=False)

def battle_snapshot(b):
    snap=b.snapshot() if b else None
    if snap:
        rt=b.runtime[b.active_weapon_id]
        snap.update(yaw=b.player.yaw,pitch=b.player.pitch,fov=b.fov,aiming=b.player.aiming,level=b.level.level_id,lock_seconds=b.stats.lock_seconds,
            weapon_category=b.stats.category,fire_mode=b.stats.fire_mode,magazine_capacity=b.stats.magazine_size,
            lock_box_scale=b.stats.lock_box_scale,lock_ready=b.lock.ready(),lock_valid=list(b.lock.valid),lock_current=b.lock.current,cooldown_seconds=b.stats.interval,
            lock_progress=1 if b.lock.ready() else min((b.lock.progress.get(k,0) for k in b.lock.valid),default=0),
            fire_blocked=can_fire(b,rt),
            reload_remaining=max(0,(rt.reload_finish_at or b.elapsed)-b.elapsed),cooldown_remaining=max(0,rt.next_shot_at-b.elapsed,rt.next_burst_start_at-b.elapsed if b.stats.fire_mode=='burst' else 0),
            weapon_error=ERRORS.get(can_fire(b,rt),can_fire(b,rt)) if b.phase=='active' else None)
        for item in snap['aircraft']:
            a=b.aircraft[item['id']];item.update(kind=a.kind,yaw=a.yaw,pitch=a.pitch)
        for item in snap['enemies']: item['kind']=b.enemies[item['id']].kind
        for item in snap['turrets']:
            turret=b.turrets[item['id']];target=b.aircraft.get(turret.target_id) or b.enemies.get(turret.target_id)
            endpoint=target.center.tuple() if target else next((e['target'] for e in reversed(b.events) if e['kind']=='turret_fire' and e['source_id']==turret.id),None)
            item.update(target_id=turret.target_id,origin=turret.center.tuple(),target_position=endpoint)
        for kind,objects in (('missiles',b.missiles),('rockets',b.rockets)):
            for item in snap[kind]:
                projectile=objects[item['id']]
                item.update(forward=projectile.forward.tuple(),weapon_id=projectile.weapon_id,age=projectile.age)
    return snap

def state_json(message=None,transaction_result=None):
    global ui_generation,ui_route
    b=app.battle
    route=(app.screen,app.slot,(app.profile or {}).get('profile_id'),id(app.draft) if app.draft else None,b.attempt_id if b else None,b.phase if b else None)
    if route!=ui_route:ui_generation+=1;ui_route=route
    snap=battle_snapshot(b)
    return json.dumps(dict(screen=app.screen,generation=ui_generation,profile=app.profile,slot=app.slot,cursor=app.cursor,draft=app.draft.loadout if app.draft else None,battle=snap,result=app.last_result,error=app.error,message=message,transaction_result=transaction_result,quotes=upgrade_quotes(),shop=shop_details() if app.screen=='store' else None,slots=app.repository.list_slots() if app.screen=='slot_select' else None,delete_confirmation=delete_confirmation),ensure_ascii=False)

WEAPON_STAT_FIELDS=('base_damage','interval','burst_interval','range','magazine_size','reload_seconds','pellet_count','spread_angle','lock_seconds','lock_box_scale','aim_assist','aim_factor','quota','projectile_speed','blast_radius')
def weapon_stats(profile,wid):
    stats=resolve_weapon_stats(profile,wid)
    return {key:getattr(stats,key) for key in WEAPON_STAT_FIELDS}

def changed_stats(before,after):
    return {key:dict(before=value,after=after[key]) for key,value in before.items() if value!=after.get(key)}

_shop_key=None
_shop=None
def shop_details():
    global _shop_key,_shop
    from copy import deepcopy
    p=app.profile
    if not p:return None
    key=(p['profile_id'],p['profile_revision'])
    if key==_shop_key:return _shop
    weapons={}
    for wid in WEAPONS:
        candidate=deepcopy(p)
        if wid not in candidate['owned_weapons']:candidate['owned_weapons'][wid]=new_weapon()
        before=weapon_stats(candidate,wid);attachments={}
        if wid in p['owned_weapons']:
            for aid,a in ATTACHMENTS.items():
                if wid not in a.applicable_weapons:continue
                preview=deepcopy(candidate);w=preview['owned_weapons'][wid]
                equipped=w['selected_attachments'][a.slot]==aid
                w['selected_attachments'][a.slot]=None if equipped else aid
                attachments[aid]=dict(equipped=equipped,changes=changed_stats(before,weapon_stats(preview,wid)))
        weapons[wid]=dict(stats=before,attachments=attachments)
    _shop=dict(weapons=weapons,player=asdict(resolve_player_stats(p)),armors={aid:asdict(resolve_player_stats(p,aid)) for aid in ARMORS})
    _shop_key=key
    return _shop

_quote_key=None
_quotes=None
def upgrade_quotes():
    """向同一交易規則試算報價，避免顯示價格另有一套公式。"""
    global _quote_key,_quotes
    p=app.profile
    if not p:return None
    key=(p['profile_id'],p['profile_revision'])
    if key==_quote_key:return _quotes
    from copy import deepcopy
    from uuid import uuid4
    from air_defense.progression import transact
    def quote(kind,**fields):
        candidate=deepcopy(p);candidate['coins']=10**12
        result=transact(candidate,uuid4().hex,dict(kind=kind,profile_id=p['profile_id'],rebirth_count=p['rebirth_count'],**fields))
        wid=fields.get('weapon_id');before=weapon_stats(p,wid) if wid else asdict(resolve_player_stats(p));after=weapon_stats(candidate,wid) if wid else asdict(resolve_player_stats(candidate))
        return dict(price=-result['summary']['coins_delta'],available=result['result_code']=='applied',reason=ERRORS.get(result['reason'],result['reason']),changes=changed_stats(before,after))
    _quotes=dict(player=quote('upgrade_player',upgrade_id='max_hp'),weapons={wid:{key:quote('upgrade_weapon',weapon_id=wid,upgrade_id=key) for key in UPGRADE_PRICES if applicable_upgrade(wid,key)} for wid in p['owned_weapons']})
    _quote_key=key
    return _quotes

def dispatch(raw):
    global delete_confirmation
    req=json.loads(raw);action=req['action'];p=req.get('payload',{});message=None;transaction_result=None
    expected=req.get('expected')
    if expected and (expected.get('generation')!=ui_generation or expected.get('screen')!=app.screen or expected.get('revision')!=(app.profile or {}).get('profile_revision')):
        return state_json('畫面已更新，請依目前內容重新操作。')
    try:
        if action=='select_slot' and app.screen=='slot_select' and not delete_confirmation:
            app.select_slot(int(p['slot']))
            app.repository.touch(app.slot,force=True)
        elif action=='request_delete' and app.screen=='slot_select' and not app.pending_save:
            if delete_confirmation: app.repository.cancel_delete(delete_confirmation['token'])
            delete_confirmation=app.repository.request_delete(int(p['slot']))
        elif action=='cancel_delete':
            if delete_confirmation: app.repository.cancel_delete(delete_confirmation['token'])
            delete_confirmation=None
        elif action=='confirm_delete' and app.screen=='slot_select' and not app.pending_save:
            confirmation=delete_confirmation
            delete_confirmation=None
            if not confirmation or confirmation['token']!=p.get('token') or confirmation['slot']!=p.get('slot'):
                raise SaveError('confirmation','請重新確認要刪除的存檔。')
            app.repository.confirm_delete(p['slot'],p['token'])
            if app.slot==p['slot']:
                if app.battle:app.battle.teardown()
                app.profile=None;app.slot=None;app.draft=None;app.battle=None;app.last_result=None;app.cursor=(1,1)
            message=f"已刪除存檔 {p['slot']}，可以建立新進度。"
        elif action=='prepare':app.begin_preparation()
        elif action=='next':message=app.next_preparation()
        elif action=='back':app.back_preparation()
        elif action=='armor':message=app.set_draft_armor(p.get('id'))
        elif action=='weapon':message=app.set_draft_slot(int(p['slot']),p.get('id'))
        elif action=='place':message=app.place_turret(p['id'],p['x'],p['z'])
        elif action=='remove':app.remove_turret(p['id'])
        elif action=='party_confirm':
            if app.confirm_and_start():app.show_menu()
        elif action=='start':app.confirm_and_start()
        elif action=='pause' and app.battle:
            app.battle.pause()
            if not app.pending_save:app.repository.touch(app.slot,force=True)
        elif action=='resume' and app.battle:app.battle.resume()
        elif action=='menu':
            if app.screen=='battle' and app.battle and app.battle.phase in ('active','paused'):app.leave_battle()
            else:app.show_menu()
        elif action=='slots' and not app.pending_save:app.leave_battle();app.screen='slot_select'
        elif action=='store' and not app.pending_save:app.screen='store'
        elif action=='transaction':
            r=app.transaction(p.pop('kind'),**p);message=r.get('reason');transaction_result=r
        elif action=='rebirth':message=app.rebirth()
        elif action=='retry':app.retry_save()
        elif action=='tick' and app.battle and app.screen=='battle':
            commands=tuple(InputCommand(**c) for c in p.pop('commands',[]))
            dt=p.pop('dt');app.battle.aspect=p.pop('aspect',16/9)
            app.battle.advance(dt,InputFrame(commands=commands,**p));app.settle()
            if app.battle.phase=='active' and not app.pending_save:app.repository.touch(app.slot)
    except (SaveError,ValueError,KeyError,TypeError) as e:message=str(e)
    return state_json(ERRORS.get(message,message),transaction_result)


party_battle=None
def party_start(raw):
    global party_battle
    from air_defense.multiplayer import CooperativeBattle
    from air_defense.progression import level_for
    data=json.loads(raw)
    members=[dict(id=m['id'],name=m['name'],profile=validate_profile(m['profile'])) for m in data['roster']]
    party_battle=CooperativeBattle(members,level_for(*data['level']),data['runId'])
    return party_snapshot()

def party_snapshot():
    views={}
    for key,actor in party_battle.actors.items():
        view=battle_snapshot(actor)
        view.update(attempt_id=party_battle.attempt_id,phase=party_battle.phase,players=party_battle.roster_snapshot(),self_id=key,
                    party_size=party_battle.count,events=party_battle.events,cooperative=True,input_ack=getattr(actor,'input_ack',0),input_stream=getattr(actor,'input_stream',None),command_ack=actor.last_command,look_total_ack=getattr(actor,'look_total',[0,0]))
        views[key]=view
    return json.dumps(dict(phase=party_battle.phase,views=views),ensure_ascii=False)

def party_tick(raw):
    data=json.loads(raw);frames={}
    for key,item in data['frames'].items():
        if key not in party_battle.actors:continue
        actor=party_battle.actors[key]
        actor.input_ack=item.get('ackInput',getattr(actor,'input_ack',0))
        if item.get('departed'):actor.player.hp=0
        if item.get('suspended'):
            actor.held=False;actor.require_release=True;actor.lock.clear();actor.player.aiming=False
            frames[key]=InputFrame();continue
        if item.get('stream') and item['stream']!=getattr(actor,'input_stream',None):
            actor.input_stream=item['stream'];actor.last_command=-1;actor.held=False;actor.look_total=[0,0]
        commands=tuple(InputCommand(**c) for c in item.get('commands',[])[:96] if c.get('kind') in ('fire_down','fire_up','select_slot','toggle_aim','reload','jump'))
        actor.aspect=max(.2,min(6,float(item.get('aspect',16/9))))
        look=item.get('look_delta',[0,0])
        if 'look_total' in item:
            total=item['look_total'];previous=getattr(actor,'look_total',[0,0]);look=[total[0]-previous[0],total[1]-previous[1]];actor.look_total=total
        frames[key]=InputFrame(move_x=max(-1,min(1,float(item.get('move_x',0)))),move_z=max(-1,min(1,float(item.get('move_z',0)))),
                               look_delta=tuple(max(-180,min(180,float(v))) for v in look[:2]),commands=commands)
    party_battle.advance_group(data['dt'],frames)
    return party_snapshot()

def party_reward(raw):
    from copy import deepcopy
    from air_defense.progression import transact
    from air_defense.state import PendingSave
    receipt=json.loads(raw)
    if app.pending_save:return state_json('請先重試保存')
    if not app.profile or app.profile['profile_id']!=receipt['profile_id'] or app.profile['rebirth_count']!=receipt['rebirth']:
        return state_json('此獎勵屬於出戰時的存檔與重生輪次。')
    if receipt['reward']<=0:return state_json()
    candidate=deepcopy(app.profile)
    request=dict(kind='coop_reward',profile_id=receipt['profile_id'],rebirth_count=receipt['rebirth'],a=receipt['level_a'],b=receipt['level_b'],A=receipt['campaign'],party_size=receipt['party_size'])
    result=transact(candidate,receipt['run_id'],request)
    if result['result_code']!='applied' or result['coins_delta']!=receipt['reward']:
        return state_json('獎勵驗證失敗，尚未更改存檔。')
    try:app.repository.save(app.slot,candidate)
    except SaveError as exc:
        app.pending_save=PendingSave(candidate,receipt['run_id'],result,'profile_menu');app.screen='save_error';app.error=str(exc)
        return state_json()
    app.profile=candidate
    return state_json()


# PvP 使用獨立入口，不讀取 app、Repository 或合作交易。
from air_defense.pvp import PvpBattle, predict as predict_pvp_actor
pvp_battle = None


def pvp_start(raw):
    global pvp_battle
    data = json.loads(raw)
    pvp_battle = PvpBattle(data['runId'], data['roster'], data['timeLimitSeconds'])
    return json.dumps(pvp_battle.snapshot(), ensure_ascii=False, allow_nan=False)


def pvp_tick(raw):
    if pvp_battle is None:
        raise ValueError('對戰尚未開始')
    data = json.loads(raw)
    return json.dumps(pvp_battle.advance(data['dt'], data.get('frames', {}), data.get('departedIds', [])), ensure_ascii=False, allow_nan=False)


def pvp_predict(raw):
    data = json.loads(raw)
    return json.dumps(predict_pvp_actor(data['actor'], data['frames']), ensure_ascii=False, allow_nan=False)


def pvp_dispose(raw='{}'):
    global pvp_battle
    pvp_battle = None
    return '{}'
