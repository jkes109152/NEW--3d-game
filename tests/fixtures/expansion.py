"""新版測試資料與隔離位置，不由待測公式生成預期值。"""
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import os

PROFILE_ID = '1' * 32

def operation_id(number=1):
    return f'{number:032x}'

def owned_weapon():
    return dict(upgrade_levels=dict(damage=0, cooldown=0, range=0, lock_time=0, whitebox=0, aim_assist=0),
                owned_attachments=[], selected_attachments=dict(optic=None, barrel=None, feed=None),
                owned_colors=['original'], selected_color='original', owned_patterns=['plain'], selected_pattern='plain')

def profile(coins=0, rebirth_count=0):
    return dict(schema_version=2, profile_id=PROFILE_ID, coins=coins, rebirth_count=rebirth_count,
                profile_revision=0, rebirth_available=False, last_completed_a_b=None, player_upgrades={'max_hp':0},
                owned_weapons={key:owned_weapon() for key in ('W01','W17','W03')}, owned_armors=[], owned_turrets=[],
                confirmed_loadout=dict(armor_id=None, weapon_slots=['W01','W17','W03',None,None], deployments=[]),
                operation_history=[])

def request(p, kind, **fields):
    return dict(kind=kind, profile_id=p['profile_id'], rebirth_count=p['rebirth_count'], **fields)


def equipped(weapon_id='W03', **kwargs):
    from air_defense.state import BattleState
    from air_defense.progression import level_for
    p=profile()
    p['owned_weapons'].setdefault(weapon_id,owned_weapon())
    slots=['W01',weapon_id,None,None,None] if weapon_id!='W01' else ['W01','W03',None,None,None]
    if weapon_id=='W02':slots[2]='W03'
    p['confirmed_loadout']['weapon_slots']=slots
    b=BattleState(p,level_for(1,1,2),**kwargs)
    b.select_weapon(2 if weapon_id!='W01' else 1)
    return b


def start_prepared(app, seed=1701):
    app.begin_preparation()
    for _ in range(3):
        assert app.next_preparation() is None
    return app.confirm_and_start(seed=seed)

@contextmanager
def isolated_roots():
    with TemporaryDirectory(prefix='防守-v2-') as folder:
        root=Path(folder)
        with patch.dict(os.environ, {'LOCALAPPDATA':str(root), 'AIR_DEFENSE_V2_SAVE_DIR':str(root/'new')}):
            yield root/'new', root/'AirDefenseQuality'
