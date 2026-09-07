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
# 掩體位於路線兩側；中央保留敵兵可通行走廊。
COVERS = ((-29,1,76,8,2,3),(28,1,65,8,2,3),(-26,1.2,43,9,2.4,3),
          (27,1.2,17,9,2.4,3),(-28,1,-5,8,2,3),(28,1,-30,8,2,3))
AIRCRAFT = {
    'NORMAL': (1,26.,24.,.25,48.,22.,'#e8735e'),
    'MANPOWER_SUPPORT': (1,34.,16.,.20,34.,16.,'#e2ae61'),
    'FAST': (1,16.,32.,.40,70.,30.,'#69bee9'),
    'ARMORED_BOSS': (5,60.,20.,.22,30.,14.,'#bd8ddb'),
}
ERRORS = {'applied':'操作完成','weapon_locked':'武器尚未解鎖','phase':'目前無法攻擊',
          'target_type':'請瞄準合法目標','dead':'目標已消滅','blocked':'目標被掩體遮蔽',
          'range':'目標超出射程','cooldown':'武器冷卻中','ammo':'本關 RPG 彈藥已用完',
          'lock':'保持瞄準，等待鎖定完成','maxed':'已達升級上限','prerequisite_missing':'請先解鎖陸地自動防禦',
          'insufficient_coins':'金幣不足','invalid_id':'無效的項目','rebirth_unavailable':'失敗或完成最終關後才能重生',
          'operation_conflict':'操作識別不一致，已拒絕重複要求','save_failed':'尚未保存，請重試',
          'player':'防守者倒下','city':'城市防線失守','impact':'敵機突破防空線'}

ERRORS.update(ok='操作完成',not_owned='尚未擁有此項目',already_owned='已經擁有',incompatible='此配件或升級不適用',cap_reached='已達本輪上限',locked='首次重生後開放',invalid_loadout='請檢查配置',invalid_slots='請配置五個槽位',duplicate_weapon='同一武器不可重複',missing_target_kind='至少攜帶一把防空與一把對地武器',capacity='超過本輪部署容量',outside_map='請放在地圖範圍內',blocked_ground='此處有障礙物',spawn_reserved='請避開玩家出生區',route_reserved='請避開敵軍通道',overlap='砲塔距離必須至少三公尺',invalid_position='無效的放置位置',stale_draft='配置已過期，請重新準備',not_eligible='尚未取得重生資格',reload='換彈中',ammo='彈藥已用完',stale_round='此操作屬於先前輪次',invalid_round='輪次不符',profile_mismatch='紀錄身分不符',invalid_request='交易資料無效')
