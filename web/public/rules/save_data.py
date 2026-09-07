"""封閉 JSON 驗證、原子寫入、五欄位與故障復原。"""
from pathlib import Path
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
import re
import threading
import uuid
import hashlib
from .progression import new_profile, ProfileV2, transact

class SaveError(Exception):
    def __init__(self,code,message):
        super().__init__(message); self.code=code

def integer(v,minimum=0): return type(v) is int and v>=minimum

def validate_profile(data):
    from .deployment import finite_coordinate
    from .catalog import WEAPONS, ARMORS, TURRETS, ATTACHMENTS, UPGRADE_PRICES, COLORS, PATTERNS, applicable_upgrade, upgrade_cap
    from .progression import valid_id, new_weapon, REQUEST_FIELDS
    def require(ok,message='存檔資料無效'):
        if not ok: raise ValueError(message)
    def closed(v,keys):return type(v) is dict and set(v)==set(keys)
    def unique(v,allowed):return type(v) is list and all(type(k) is str and k in allowed for k in v) and len(set(v))==len(v)
    require(closed(data,ProfileV2.__annotations__),'存檔欄位不完整或含未知欄位')
    require(type(data['schema_version']) is int and data['schema_version']==2,'不支援的存檔版本')
    require(valid_id(data['profile_id']),'玩家識別字無效')
    for key in ('coins','rebirth_count','profile_revision'):require(integer(data[key]),key+' 必須是非負整數')
    require(type(data['rebirth_available']) is bool)
    r=data['rebirth_count'];cap=upgrade_cap(r)
    require(closed(data['player_upgrades'],['max_hp']) and integer(data['player_upgrades']['max_hp']) and data['player_upgrades']['max_hp']<=cap)
    owned=data['owned_weapons'];require(type(owned) is dict and all(type(k) is str and k in WEAPONS for k in owned) and {'W01','W03','W17'}<=set(owned))
    for wid,w in owned.items():
        require(closed(w,new_weapon()));levels=w['upgrade_levels'];require(closed(levels,UPGRADE_PRICES))
        for key,value in levels.items():require(integer(value) and value<=(1 if key=='aim_assist' else cap) and (applicable_upgrade(wid,key) or value==0))
        require(unique(w['owned_attachments'],ATTACHMENTS) and all(wid in ATTACHMENTS[k].applicable_weapons for k in w['owned_attachments']))
        require(closed(w['selected_attachments'],['optic','barrel','feed']))
        for slot,key in w['selected_attachments'].items():require(key is None or type(key) is str and key in w['owned_attachments'] and ATTACHMENTS[key].slot==slot)
        for plural,selected,catalog,default in [('owned_colors','selected_color',COLORS,'original'),('owned_patterns','selected_pattern',PATTERNS,'plain')]:
            require(unique(w[plural],catalog) and default in w[plural] and type(w[selected]) is str and w[selected] in w[plural])
    require(unique(data['owned_armors'],ARMORS))
    towers=data['owned_turrets'];require(type(towers) is list and (r>0 or not towers));instances=set()
    for tower in towers:
        require(closed(tower,['instance_id','turret_id']))
        key=tower['instance_id'];require(type(key) is str and key.startswith('turret-') and valid_id(key[7:]) and key not in instances)
        require(type(tower['turret_id']) is str and tower['turret_id'] in TURRETS);instances.add(key)
    load=data['confirmed_loadout'];require(closed(load,['armor_id','weapon_slots','deployments']))
    require(load['armor_id'] is None or type(load['armor_id']) is str and load['armor_id'] in data['owned_armors'])
    slots=load['weapon_slots'];require(type(slots) is list and len(slots)==5);seen=set()
    for key in slots:
        require(key is None or type(key) is str and key in owned and key not in seen)
        if key:seen.add(key)
    require(type(load['deployments']) is list);seen=set()
    for tower in load['deployments']:
        require(closed(tower,['instance_id','x','z']));key=tower['instance_id']
        require(type(key) is str and key in instances and key not in seen);seen.add(key)
        for axis in ('x','z'):require(finite_coordinate(tower[axis]))
    last=data['last_completed_a_b']
    require(last is None or closed(last,['a','b']) and all(integer(v,1) for v in last.values()) and last['a']<=r+2 and last['b']<=2*last['a']+1)
    require(type(data['operation_history']) is list);seen=set();previous=0
    for op in data['operation_history']:
        require(closed(op,['operation_id','kind','request_fingerprint','result_code','reason','profile_revision','rebirth_count','summary']))
        require(valid_id(op['operation_id']) and op['operation_id'] not in seen);seen.add(op['operation_id'])
        require(type(op['kind']) is str and op['kind'] in REQUEST_FIELDS and op['result_code'] in ('applied','rejected') and type(op['reason']) is str)
        require(type(op['request_fingerprint']) is str and re.fullmatch('[0-9a-f]{64}',op['request_fingerprint']))
        require(integer(op['profile_revision'],1) and previous<op['profile_revision']<=data['profile_revision']);previous=op['profile_revision']
        require(integer(op['rebirth_count']) and op['rebirth_count']<=r)
        summary=op['summary'];require(type(summary) is dict and type(summary.get('coins_delta')) is int)
        fields={'coins_delta'}
        kind=op['kind']
        if op['result_code']=='applied':
            require(op['reason']=='ok')
            fields|={
             'purchase_weapon':{'weapon_id'},'purchase_armor':{'armor_id'},'purchase_turret':{'turret_id','instance_id'},
             'upgrade_player':{'upgrade_id','new_level'},'upgrade_weapon':{'weapon_id','upgrade_id','new_level'},
             'purchase_attachment':{'weapon_id','attachment_id'},'purchase_cosmetic':{'weapon_id','cosmetic_kind','cosmetic_id'},
             'customize_weapon':{'weapon_id'},'confirm_loadout':{'deployed_count'},'reward':{'a','b','A'},'failure':{'a','b','A'},'rebirth':{'previous_rebirth_count','new_rebirth_count'}}[kind]
        else:require(summary['coins_delta']==0 and op['reason'] in {'already_owned','insufficient_coins','not_owned','incompatible','cap_reached','locked','not_eligible','invalid_id','stale_round','invalid_round','invalid_loadout','invalid_slots','duplicate_weapon','missing_target_kind','capacity','outside_map','blocked_ground','spawn_reserved','route_reserved','overlap','invalid_position','duplicate_instance'})
        require(set(summary)==fields)
        for k,v in summary.items():
            if k in ('new_level','deployed_count','a','b','A','previous_rebirth_count','new_rebirth_count'):require(integer(v))
            elif k!='coins_delta':require(type(v) is str)
        for field,catalog in [('weapon_id',WEAPONS),('armor_id',ARMORS),('turret_id',TURRETS),('attachment_id',ATTACHMENTS)]:
            if field in summary:require(summary[field] in catalog)
        if op['result_code']=='applied':
            if kind.startswith('purchase_') or kind.startswith('upgrade_'):require(summary['coins_delta']<=0)
            if kind in ('customize_weapon','confirm_loadout','failure'):require(summary['coins_delta']==0)
            if 'upgrade_id' in summary:
                require(summary['upgrade_id']=='max_hp' if kind=='upgrade_player' else applicable_upgrade(summary['weapon_id'],summary['upgrade_id']))
                require(1<=summary['new_level']<=(1 if summary['upgrade_id']=='aim_assist' else upgrade_cap(op['rebirth_count'])))
            if kind=='purchase_turret':require(summary['instance_id']=='turret-'+op['operation_id'])
            if kind=='confirm_loadout':require(summary['deployed_count']<=2*op['rebirth_count'])
            if kind in ('reward','failure'):
                from .progression import level_for
                require(summary['A']==op['rebirth_count']+2)
                level=level_for(summary['a'],summary['b'],summary['A'])
                require(summary['coins_delta']==(level.reward if kind=='reward' else 0))
            if kind=='rebirth':require(summary['previous_rebirth_count']==op['rebirth_count'] and summary['new_rebirth_count']==op['rebirth_count']+1 and summary['coins_delta']<=0)
            if kind=='purchase_cosmetic':
                require(summary['cosmetic_kind'] in ('color','pattern'))
                require(summary['cosmetic_id'] in (COLORS if summary['cosmetic_kind']=='color' else PATTERNS))
    result=deepcopy(data)
    result['owned_armors'].sort()
    for w in result['owned_weapons'].values():
        for key in ('owned_attachments','owned_colors','owned_patterns'):w[key].sort()
    return result


def strict_object(pairs):
    out={}
    for key,value in pairs:
        if key in out: raise ValueError('重複 JSON 欄位')
        out[key]=value
    return out

def atomic_json(path,data):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    try:
        with temp.open('x',encoding='utf-8') as f:
            json.dump(data,f,ensure_ascii=False,allow_nan=False,indent=2); f.flush(); os.fsync(f.fileno())
        os.replace(temp,path)
    finally:
        temp.unlink(missing_ok=True)

class SlotRepository:
    def __init__(self,root=None):
        old=(Path(os.environ.get('LOCALAPPDATA',Path.home()))/'AirDefenseQuality').resolve()
        self.root=Path(root or os.environ.get('AIR_DEFENSE_V2_SAVE_DIR') or old.with_name('AirDefenseQualityV2')).resolve()
        if self.root==old or old in self.root.parents:raise ValueError('新版資料位置不能使用舊版資料夾')
        self.lock=threading.RLock(); self.tokens={}; self.recovery_backups={}

    def path(self,slot):
        if type(slot) is not int or not 1<=slot<=5: raise ValueError('存檔欄位必須介於 1 至 5')
        return self.root/f'slot-{slot}.json'

    def load(self,slot):
        with self.lock:
            path=self.path(slot)
            try: raw=path.read_text(encoding='utf-8')
            except FileNotFoundError: return None
            except UnicodeError as exc: raise SaveError('corrupt','存檔不是有效 UTF-8；原始檔案已保留，可備份後重建。') from exc
            except OSError as exc: raise SaveError('read_failed','無法讀取存檔：'+str(exc)) from exc
            try: return validate_profile(json.loads(raw,object_pairs_hook=strict_object,parse_constant=lambda x:(_ for _ in ()).throw(ValueError(x))))
            except (ValueError,TypeError,UnicodeError,RecursionError) as exc: raise SaveError('corrupt','存檔損壞或版本不支援；原檔已保留。'+str(exc)) from exc

    def save(self,slot,data):
        with self.lock:
            valid=validate_profile(data)
            try: atomic_json(self.path(slot),valid)
            except OSError as exc: raise SaveError('save_failed','尚未保存；記憶體進度保留，可重試。'+str(exc)) from exc

    def create(self,slot):
        with self.lock:
            if self.path(slot).exists(): raise SaveError('exists','欄位已有資料，請先載入或確認復原')
            p=new_profile(); self.save(slot,p); return p

    def list_slots(self):
        rows=[]
        for slot in range(1,6):
            try: rows.append((slot,self.load(slot),None))
            except SaveError as exc: rows.append((slot,None,str(exc)))
        return rows

    def transaction(self,slot,p,op,request):
        with self.lock:
            self.path(slot)
            validate_profile(p)
            code=transact(p,op,request)
            if code['result_code']!='operation_conflict' and not code['replayed']: self.save(slot,p)
            return code

    def prepare_recovery(self,slot,expected_digest=None):
        """在顯示重建確認前保存原始位元組；重複預覽沿用相同備份。"""
        with self.lock:
            path=self.path(slot)
            if path.exists():
                try: raw=path.read_bytes()
                except OSError as exc: raise SaveError('backup_failed','讀取備份來源失敗，禁止重建。') from exc
                digest=hashlib.sha256(raw).hexdigest()
                if expected_digest is not None and digest!=expected_digest:
                    raise SaveError('recovery_changed','原始檔案已變更，請返回選檔重新確認；目前檔案已保留。')
                previous=self.recovery_backups.get(slot)
                if previous and previous[0]==digest:
                    try:
                        if hashlib.sha256(previous[1].read_bytes()).hexdigest()==digest: return previous[1]
                    except OSError:
                        pass  # 無法驗證舊備份時重新建立，成功前不得覆寫原檔。
                stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
                backup=path.with_name(f'slot-{slot}.corrupt.{stamp}.json')
                if backup.exists(): backup=path.with_name(f'slot-{slot}.corrupt.{stamp}.{uuid.uuid4().hex[:8]}.json')
                try:
                    with backup.open('xb') as out: out.write(raw); out.flush(); os.fsync(out.fileno())
                except OSError as exc: raise SaveError('backup_failed','備份失敗，禁止重建；原檔保留。') from exc
                self.recovery_backups[slot]=(digest,backup)
                return backup
            if expected_digest is not None:
                raise SaveError('recovery_changed','原始檔案已移除，請返回選檔重新確認。')

    def recover(self,slot,confirm=False):
        if not confirm: return None
        with self.lock:
            previous=self.recovery_backups.get(slot)
            self.prepare_recovery(slot,expected_digest=previous[0] if previous else None)
            p=new_profile(); self.save(slot,p)
            self.recovery_backups.pop(slot,None)
            return p

    def _delete_snapshot(self,slot):
        snapshot=[]
        for path in [self.path(slot),*sorted(self.root.glob(f'slot-{slot}.corrupt.*.json'))]:
            try:digest=hashlib.sha256(path.read_bytes()).hexdigest()
            except FileNotFoundError:digest=None
            snapshot.append((path,digest))
        return tuple(snapshot)

    def request_delete(self,slot):
        with self.lock:
            try:snapshot=self._delete_snapshot(slot)
            except OSError as exc:raise SaveError('delete_failed','無法讀取刪除目標，請稍後重試；資料已保留。') from exc
            token=uuid.uuid4().hex; self.tokens[token]=(slot,snapshot); return token

    def cancel_delete(self,token): self.tokens.pop(token,None)

    def confirm_delete(self,slot,token):
        with self.lock:
            confirmation=self.tokens.get(token)
            if confirmation is None or confirmation[0]!=slot: return False
            # 其餘舊確認不得在同欄位重新建立後刪除新資料。
            self.tokens={key:value for key,value in self.tokens.items() if value[0]!=slot}
            try:
                if self._delete_snapshot(slot)!=confirmation[1]:return False
                for path,_ in confirmation[1]: path.unlink(missing_ok=True)
            except OSError as exc: raise SaveError('delete_failed','刪除未完成，請重新選擇欄位。') from exc
            self.recovery_backups.pop(slot,None)
            return True
