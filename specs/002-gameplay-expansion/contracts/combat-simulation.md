# 戰鬥模擬與輸入契約

**依據**：[資料模型](../data-model.md)、[數值表](../balance.md)；數值以附表為準，不在呈現層再定義一份。

## 模組邊界與入口

- `resolve_weapon_stats(profile, weapon_id)`、`resolve_player_stats(profile, armor_id)` 位於 loadout；只讀目錄及擁有資料，回不可變能力。
- `BattleState(profile_snapshot, level, loadout_snapshot, seed, attempt_id)` 僅由準備確認成功的 AppState 建立；不預設六塔或固定槽號。
- `can_fire(battle, weapon_runtime) -> reason | None` 驗階段、持有、冷卻、上膛、換彈與彈藥；防空另驗瞄準、可見性、射程及鎖定。一般槍與火箭不要求先有命中目標。
- `try_fire(...) -> FireResult` 先完成所有可發射檢查，再一次扣資源、設時刻及建立射擊；多目標導彈先建立完整快照再提交，建立失敗不得扣半份資源。
- `raycast_hit(origin, direction, max_distance, targets, world) -> CollisionHit | None`、`sweep_projectile(projectile, dt, targets, world)` 與 `apply_explosion(...)` 是純規則，不依賴場景 Entity。
- `validate_deployment` 與 `query_turret_target` 共用 `WorldDefinition`、水平距離與可見性；地面 Boss 傷害為 min(請求傷害, max(0, hp−max_hp/2))，一般敵人限制不超過剩餘 HP。

## 輸入與固定時間

`InputFrame` 包含 `move_x`、`move_z`、`look_delta` 及有序 `commands`。commands 的項目恰有 sequence、kind、value；kind 為 fire_down、fire_up、reload、select_slot、toggle_aim、jump、pause，value 只在 select_slot 使用整數 1～5，其餘為 null。

- Controller 在原生事件當下遞增 sequence；不足一個 1/120 秒固定步時佇列保留，不能用布林 OR 抹去同一步前的按下與放開。持續移動／視角另按有效模擬時間處理。
- 一次固定步按 sequence 消費 commands；fire_down 是一次「開始按住」，已 held 的重複 down 不產生新的半自動射擊。fire_up 清 held；全自動在後續步依 held 發射。
- 任何 pause／失焦具有停止優先權：該批輸入不再發射，清命令與尚未射出點放，require_release=true。恢復後必須收到 fire_up 才解除，避免仍按住滑鼠即開火。
- 半自動／手動上膛只對新 down 試射；冷卻或換彈中 down 被消費，不留待就緒後補射。點放有自己的三發剩餘、彈間與下一次首發時刻；不足三發只消耗實有子彈。
- 時間使用有效模擬秒數的到期時刻。持續開火下一到期=`上一到期＋有效間隔`，保留跨步餘量，不每發改成 `現在＋間隔`。重新按下／換彈完成後的第一發由目前時間開始，不追補不可射擊期間。
- 保留 SimulationClock 的 1/120 秒及每幀最多八步，捨棄超出追算量的長時間積壓。30／60／144 Hz 測試以相同有效模擬時間比較結果；暫停不累積時間。

## 每步更新順序

1. 檢查當局有效、暫停／失焦；若停止立即返回。
2. 更新玩家移動、視角、裝甲回血及到期換彈；保留離散命令順序供第 4 步消費。
3. 推進飛機及敵兵位置，重新計算可見性與鎖定，辨識本步撞城、玩家或城市死亡。
4. 若已有失敗立即結束，不再發射或發獎勵；否則依 sequence 消費玩家命令，每個 down 以當下所選武器立即試射，之後處理已排定點放／全自動及砲塔。先射擊再切槍不取消已發彈體；先切槍再射擊使用新武器，不能只用該批命令的最後槽位處理所有射擊。
5. 推進防空導彈與火箭至本步允許路徑，按首次接觸結算傷害與爆炸，建立唯一空降批次；同一彈體命中與到期相遇時有效路徑內命中優先。
6. 整理死亡／到期物件並判定完成；已有失敗優先於成功，全部空地威脅清除才成功。
7. 回傳唯讀快照、有序事件與統計。每個 sequence 單調增加，attempt_id 不符的事件由所有消費者忽略。

在實作中保留現有受傷／城市判定的一致順序；若微步中同一敵人死亡則不可在其後再次攻擊，不能把步驟拆分變成死後傷害。每個命令只消費一次，當步 down 已發射後，持續開火檢查必須尊重其新到期時刻，不多送一發。新增測試鎖定這些界線。

## 彈藥、射擊與碰撞

- 每把攜帶武器各自持有 runtime；槽位更動只改選擇，不重建彈匣。切槍取消原槍進行中的換彈與未發點放，射擊／上膛冷卻照常隨有效時間經過。
- 一般子彈使用眼睛位置與準心方向查最近碰撞，終點為命中點或有效射程端點；畫面曳光可從模型槍口連到相同終點。場景包絡包含地面、掩體、城市、地圖邊界與可受擊敵人；普通子彈不對飛機扣血。
- W15／W16 八顆彈丸使用固定中心＋七顆圓環方向。每顆來源為 `(shot_id, pellet_index)`；一顆最多傷一個目標，同敵人可承受八顆，不以整次 shot 對敵人去重。
- 火箭以準心方向自眼前發射點前進，發射段也驗世界碰撞，不跳過近處牆面；模擬使用中心線與既有受擊包絡，外觀體積不擴大傷害半徑。
- 火箭本步線段先由剩餘射程與剩餘壽命截短，再驗地面 y=0、world AABB、活敵包絡。碰撞結果依距離、世界優先、穩定建立序號排序；高速穿過薄牆仍需命中。
- 爆炸距離以 contact point 到敵人中心計算；可見性起點用 contact＋normal×0.0001，避免卡在牆表面。半徑內全傷害，不穿牆、不自傷、不傷城市／塔／飛機；同一 rocket_id 對同敵人最多一次。
- 防空導彈發射快照包含 damage、source_weapon_id／turret_instance_id 及 fixed_target_id；切槍與擊殺其他目標不改傷害或追蹤目標。

## 成長與砲塔

- `difficulty_for(level)` 只依 a、b 回快照；r 僅改戰役規模、經濟及部署容量。出生時套用敵人 max_hp，空降敵人也讀相同快照。
- 航向先以向城市方向為基準，再將閃避偏航限制在有效 max_yaw_deflection；角速度使用有效 turn_rate，俯仰同樣受限。接近時間及實際位置都乘速度倍率，不只改 HUD。
- WorldDefinition 中正式編隊不新增 FAST；快速飛機使用獨立固定測試。敵兵速度及傷害維持附表。
- T01／T02 只選已落地存活敵兵，T03 只選接近中的存活飛機；排序為水平距離再 stable_order。範圍端點合法且需射線可見。
- T03 的 visible_since 自取得合法目標開始，失去可見／射程／換目標立即清零；每次發射後重新累積一秒，且仍受兩秒間隔限制。

## 快照、事件與回收

快照最少包含 attempt_id、revision、phase、elapsed、player、weapon_slots、active_weapon_id、weapon_runtime、locks、aircraft、enemies、turrets、missiles、rockets、diagnostics。player 包含有效能力、視角及 aiming_factor，UI／Scene 不再回寫 battle.fov 或能力。

事件包括 weapon_fire、reload_started、reload_finished、bolt_cycled、projectile_spawned、hit、explosion、enemy_destroyed、aircraft_destroyed、lock_complete、turret_fire、result、error；共通含 attempt_id、sequence、source_id，依種類帶 weapon_id、position、endpoints、target_id、audio_key。傷害僅在模擬層執行。

結束／取消清除火箭、導彈、點放、鎖定、待輸入及當局效果，舊事件不影響新一局。保留有界模型／效果快取須另列計數；活動物件應回到基準。

## 驗證關鍵

至少覆蓋：重排五槽、兩把火箭獨立配額、所有射擊模式、短點擊順序、0.06 秒射速、切槍換彈、暫停放開保護、射空消耗、狙擊超過 180、霰彈多顆同敵、薄牆掃掠、牆面爆炸可見性、半徑與射程端點、發射後切槍、多目標建立失敗回復、奇數 Boss 半血與超過六塔。
