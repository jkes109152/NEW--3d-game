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
from .progression import new_profile, caps, CATALOG, transact
from .config import WEAPONS

class SaveError(Exception):
    def __init__(self,code,message):
        super().__init__(message); self.code=code

def integer(v,minimum=0): return type(v) is int and v>=minimum

def validate_profile(data):
    if type(data) is not dict or set(data)!=set(new_profile()): raise ValueError('存檔欄位不完整或含未知欄位')
    if type(data['schema_version']) is not int or data['schema_version']!=1: raise ValueError('不支援的存檔版本')
    for key in ('coins','rebirth_count','profile_revision','max_aircraft_count'):
        if not integer(data[key]): raise ValueError('存檔整數欄位無效：'+key)
    if type(data['rebirth_available']) is not bool: raise ValueError('重生資格型別無效')
    r=data['rebirth_count']; levels=data['upgrade_levels']
    if type(levels) is not dict: raise ValueError('升級欄位無效')
    for key,value in levels.items():
        if key not in CATALOG or not integer(value) or value>caps(r).get(key,1): raise ValueError('無效升級等級')
    if levels.get('auto_defense_capacity',0) and not levels.get('auto_defense',0): raise ValueError('缺少砲塔前置')
    snapshot=data['upgrade_caps']
    if type(snapshot) is not dict or set(snapshot)!=set(caps(r)) or not all(integer(v) for v in snapshot.values()): raise ValueError('升級上限快照無效')
    weapons=data['unlocked_weapons']
    if type(weapons) is not list or any(type(w) is not str or w not in WEAPONS for w in weapons) or len(set(weapons))!=len(weapons): raise ValueError('武器欄位無效')
    expected=set(WEAPONS[:3])|({'RPG'} if levels.get('rpg') else set())|({'MULTI_ANTI_AIRCRAFT'} if levels.get('multi_anti_aircraft') else set())
    if set(weapons)!=expected: raise ValueError('武器解鎖與升級不一致')
    last=data['last_completed_a_b']
    if last is not None and (type(last) is not dict or set(last)!={'a','b'} or not all(integer(v,1) for v in last.values()) or last['a']>r+2 or last['b']>2*last['a']+1): raise ValueError('歷史關卡無效')
    if type(data['operation_history']) is not list: raise ValueError('操作歷史無效')
    ids=set()
    for op in data['operation_history']:
        if type(op) is not dict or set(op)!={'operation_id','kind','request_fingerprint','result_code','profile_revision','summary'}: raise ValueError('操作歷史欄位無效')
        if not isinstance(op['operation_id'],str) or not op['operation_id'] or op['operation_id'] in ids: raise ValueError('重複或無效操作 ID')
        if op['kind'] not in ('purchase','rebirth','reward','save','failure') or op['result_code'] not in ('applied','rejected','operation_conflict','failed_retryable'): raise ValueError('操作類型或結果無效')
        if not isinstance(op['request_fingerprint'],str) or not re.fullmatch('[0-9a-f]{64}',op['request_fingerprint']): raise ValueError('操作指紋無效')
        if not integer(op['profile_revision']) or op['profile_revision']>data['profile_revision'] or type(op['summary']) is not dict: raise ValueError('操作版本無效')
        ids.add(op['operation_id'])
    data=deepcopy(data); data['max_aircraft_count']=2+r; data['upgrade_caps']=caps(r)
    return data

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
        self.root=Path(root or os.environ.get('AIR_DEFENSE_SAVE_DIR') or Path(os.environ.get('LOCALAPPDATA',Path.home()))/'AirDefenseQuality')
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
            except (ValueError,TypeError,UnicodeError) as exc: raise SaveError('corrupt','存檔損壞或版本不支援；原檔已保留。'+str(exc)) from exc

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
            if code!='operation_conflict': self.save(slot,p)
            return code

    def prepare_recovery(self,slot):
        """在顯示重建確認前保存原始位元組；重複預覽沿用相同備份。"""
        with self.lock:
            path=self.path(slot)
            if path.exists():
                try: raw=path.read_bytes()
                except OSError as exc: raise SaveError('backup_failed','讀取備份來源失敗，禁止重建。') from exc
                digest=hashlib.sha256(raw).hexdigest()
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

    def recover(self,slot,confirm=False):
        if not confirm: return None
        with self.lock:
            self.prepare_recovery(slot)
            p=new_profile(); self.save(slot,p); return p

    def request_delete(self,slot):
        self.path(slot); token=uuid.uuid4().hex; self.tokens[token]=slot; return token

    def cancel_delete(self,token): self.tokens.pop(token,None)

    def confirm_delete(self,slot,token):
        with self.lock:
            if self.tokens.get(token)!=slot: return False
            # 其餘舊確認不得在同欄位重新建立後刪除新資料。
            self.tokens={key:value for key,value in self.tokens.items() if value!=slot}
            self.recovery_backups.pop(slot,None)
            try:
                for path in [self.path(slot),*self.root.glob(f'slot-{slot}.corrupt.*.json')]: path.unlink(missing_ok=True)
            except OSError as exc: raise SaveError('delete_failed','刪除未完成，請重新選擇欄位。') from exc
            return True
