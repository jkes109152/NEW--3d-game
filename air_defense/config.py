"""規格數值與固定世界配置；不匯入圖形引擎。"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / 'assets'
TICK = 1 / 120
MAX_STEPS = 8
RESOLUTIONS = ((1280, 720), (1920, 1080))
PERFORMANCE = {'warmup_seconds':10, 'sample_seconds':60, 'mean_fps':55, 'p1_fps':45, 'stall_ms':250}
QUALITY = {'low':{'shadows':False,'effects':24}, 'medium':{'shadows':True,'effects':48}, 'high':{'shadows':True,'effects':80}}
PLAYER_SPAWN = (-18., 0., 70.)
CITY_CENTER = (0., 0., -45.)
AIR_START = (0., 32., 210.)
AIR_END = (0., 10., -60.)
ROUTE = ((-16,0,68),(15,0,45),(-14,0,20),(13,0,-4),(-10,0,-27),(0,0,-45))
TURRET_POSITIONS = ((-24,0,64),(-8,0,56),(9,0,50),(24,0,36),(-20,0,8),(18,0,-18))
# 掩體位於路線兩側；中央保留敵兵可通行走廊。
COVERS = ((-29,1,76,8,2,3),(28,1,65,8,2,3),(-26,1.2,43,9,2.4,3),
          (27,1.2,17,9,2.4,3),(-28,1,-5,8,2,3),(28,1,-30,8,2,3))
AIRCRAFT = {
    'NORMAL': (1,26.,24.,.25,48.,22.,'#e8735e'),
    'MANPOWER_SUPPORT': (1,34.,16.,.20,34.,16.,'#e2ae61'),
    'FAST': (1,16.,32.,.40,70.,30.,'#69bee9'),
    'ARMORED_BOSS': (5,38.,20.,.22,30.,14.,'#bd8ddb'),
}
WEAPONS = ('ANTI_AIRCRAFT','SNIPER','PISTOL','RPG','MULTI_ANTI_AIRCRAFT')
WEAPON_NAMES = ('防空導引炮','狙擊步槍','戰術手槍','RPG 火箭筒','多目標防空炮')
COOLDOWNS = (1.25,.75,.20,2.5,1.25)
RANGES = (float('inf'),180.,12.,12.,180.)
ERRORS = {'applied':'操作完成','weapon_locked':'武器尚未解鎖','phase':'目前無法攻擊',
          'target_type':'請瞄準合法目標','dead':'目標已消滅','blocked':'目標被掩體遮蔽',
          'range':'目標超出射程','cooldown':'武器冷卻中','ammo':'本關 RPG 彈藥已用完',
          'lock':'保持瞄準，等待鎖定完成','maxed':'已達升級上限','prerequisite_missing':'請先解鎖陸地自動防禦',
          'insufficient_coins':'金幣不足','invalid_id':'無效的項目','rebirth_unavailable':'失敗或完成最終關後才能重生',
          'operation_conflict':'操作識別不一致，已拒絕重複要求','save_failed':'尚未保存，請重試',
          'player':'防守者倒下','city':'城市防線失守','impact':'敵機突破防空線'}
