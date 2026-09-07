# 資料模型：裝備庫、準備與戰鬥

**日期**：2026-09-06　**依據**：[規格](spec.md)、[數值表](balance.md)、[研究](research.md)

## 一、共同型別與識別

- `WeaponId` 固定 W01～W20，`ArmorId` 固定 A01～A06，`TurretTypeId` 固定 T01～T03；商品 ID 不因槽位、顯示名稱或排序改變。
- `ProfileId`、`OperationId`、`AttemptId` 為不含連字號的小寫 UUID 字串，由可注入工廠產生；正式使用隨機 UUID，測試可用固定合法值。
- 每台砲塔的 `instance_id` 為 `turret-` 加購買操作 ID，同筆操作永遠對應同一台；當局敵人、彈體與射擊另用 `attempt_id` 加遞增序號。
- 座標使用既有 `V3`，Y 向上；保存部署僅含 X、Z，地表 Y 固定 0。數值必須有限，拒絕 NaN、Infinity 與以 bool 冒充整數。
- 商品定義使用 frozen dataclass 與唯讀目錄，Profile 使用 TypedDict 描述的 JSON 資料及集中驗證；交易操作完整 deep-copy，不能讓巢狀清單共用到其他欄位或原候選。
- 基礎數值及升級用 `Decimal(str(value))` 解析，敵人初始生命使用精確倍率及向上取整；解析完成的當局值轉 float。傷害保留小數，生命低於 `1e-9` 歸零；空間端點容差 `1e-9`，不能把超出 0.01 視為合法。

## 二、唯讀商品與能力

| 型別 | 欄位 | 關係／規則 |
| --- | --- | --- |
| `WeaponDefinition` | id、name、category、fire_mode、target_kind、delivery、price、base_damage、interval、range、magazine_size、reload_seconds、quota、pellet_count、spread_angle、lock_seconds、lock_box_scale、projectile_speed、projectile_lifetime、blast_radius、aim_factor | 20 筆；不適用數值為 null；表列模式決定哪些必填，不能用槽位判斷 |
| `UpgradeDefinition` | id、base_price、applicable_weapons、cap_kind、effect_kind | 對應傷害、節奏、射程、鎖定、白框、輔助；自身血量另屬 player |
| `AttachmentDefinition` | id、slot、price、applicable_weapons、multipliers | 每配件唯一槽位；收益與代價同時套用 |
| `ArmorDefinition` | id、name、price、hp_delta、speed_factor、damage_reduction、regen_delay、regen_rate | 恰有六件；無裝甲為解析預設，不是第七件商品 |
| `TurretDefinition` | id、name、price、target_kind、damage、interval、range、lock_seconds | 恰有三類；實際擁有數以 instance 計 |
| `EffectiveWeaponStats` | weapon_id、所有解析後性能、upgrades、attachment_ids、color_id、pattern_id | 依基本值→個別升級→已選配件，一次解析為當局不可變快照 |
| `EffectivePlayerStats` | max_hp、move_speed、jump_height、damage_reduction、regen_delay、regen_rate、regen_budget、armor_id | 由自身血量與零／一件裝甲計算；不受其他已擁有裝甲影響 |

`catalog.py` 以 Python 定義抄錄並驗證 balance 表，遊戲執行不解析 Markdown。測試使用獨立的數值範例與目錄數量／公式不變量，避免只比對同一個函式結果。

category 固定 `anti_air`、`pistol`、`rifle`、`smg`、`shotgun`、`sniper`、`rocket`；fire_mode 固定 `semi`、`auto`、`burst`、`bolt`、`lock_single`、`lock_multi`；target_kind 固定 `aircraft`／`enemy`，delivery 固定 `hitscan`／`homing`／`rocket`。W01／W02 為兩種 lock 與 homing，W19／W20 為 semi 與 rocket，其餘依附表模式使用 hitscan。

配件 ID 固定為 `zoom_scope`、`guidance_scope`、`heavy_barrel`、`extended_magazine`、`quick_reload`、`cooling_guidance`、`light_loading_rack`；槽為 `optic`、`barrel`、`feed`。配色 ID 為 `original`、`mint`、`strawberry`、`lemon`、`grape`；圖樣為 `plain`、`dots`、`stripes`、`stars`。ID 與繁體中文名稱由目錄對應。

## 三、Profile v2 的封閉保存模型

頂層恰有以下 13 個欄位；不保留舊 `max_aircraft_count`、`upgrade_caps` 或固定武器解鎖陣列。A=2+r、升級上限與塔容量只在讀取時推導。

| 欄位 | 型別與限制 | 新檔值 |
| --- | --- | --- |
| schema_version | int，固定 2 | 2 |
| profile_id | ProfileId，建立欄位時配置，重生不變 | 新 ID |
| coins | int ≥0 | 0 |
| rebirth_count | int ≥0 | 0 |
| profile_revision | int ≥0 | 0 |
| rebirth_available | bool | false |
| last_completed_a_b | null 或恰有 a、b 的正整數物件；a≤r+2、b≤2a+1，保留歷史用途 | null |
| player_upgrades | 恰有 max_hp，int 0～min(10,5+r) | max_hp=0 |
| owned_weapons | 以 WeaponId 為鍵的 `OwnedWeapon` 字典，不可缺 W01、W17、W03 | 三把免費武器 |
| owned_armors | 不重複 ArmorId 清單，序列化依 ID 排序 | 空清單 |
| owned_turrets | `OwnedTurret` 清單，instance_id 唯一；r=0 必須空 | 空清單 |
| confirmed_loadout | `Loadout` | W01、W17、W03、null、null；無裝甲及部署 |
| operation_history | `OperationRecord` 清單，operation_id 唯一、revision 不超過目前，保留全歷史 | 空清單 |

### OwnedWeapon

恰有 `upgrade_levels`、`owned_attachments`、`selected_attachments`、`owned_colors`、`selected_color`、`owned_patterns`、`selected_pattern` 七欄位。

- `upgrade_levels` 恰含 `damage`、`cooldown`、`range`、`lock_time`、`whitebox`、`aim_assist` 六個非負整數。非適用項目必須 0，輔助最高 1，其餘最高 min(10,5+r)，新購皆為 0。
- `owned_attachments` 為不重複且相容的配件 ID 清單；`selected_attachments` 恰含 optic、barrel、feed，各為 null 或已擁有且屬該槽的 ID。
- `owned_colors` 必含 original，`owned_patterns` 必含 plain，皆為不重複有效 ID 清單；selected 必須在 owned 內。所有 owned ID 序列化排序，不影響玩家出戰槽位。
- 同一配件／外觀在另一把武器上是另一筆所有權；不保存射擊冷卻、彈匣或已解析性能。

### OwnedTurret 與 Loadout

- `OwnedTurret` 恰有 instance_id、turret_id；只保留購買身分與類型，不保存 HP 或戰鬥目標。
- `Loadout` 恰有 armor_id、weapon_slots、deployments。armor_id 為 null 或已擁有裝甲；weapon_slots 恰有五項，為已擁有且不重複武器 ID 或 null，保存空位順序。
- 每筆部署恰有 instance_id、x、z，instance_id 必須屬庫存且不得重複，x/z 必須有限數值。部署排列不改變塔的穩定建立次序，戰鬥以 instance_id 排序建立。
- 保存結構與引用錯誤屬損壞資料；空地搭配、部署容量、地圖幾何等「目前能否出戰」由準備驗證決定。歷史配置若因規則／地圖改變不再能出戰，不直接清空整個存檔。

### OperationRecord

恰有 operation_id、kind、request_fingerprint、result_code、reason、profile_revision、rebirth_count、summary。指紋為 canonical JSON 的 SHA-256 小寫十六進位字串；result_code 僅 applied／rejected。rebirth_count 記錄請求輪次，不能大於目前輪次；summary 為按交易種類限制欄位的結果摘要，不保存任意可執行內容。

重複 ID 同指紋回原結果；不同指紋為 conflict 且不寫入第二筆。保存失敗是持久化層狀態，不把已套用交易的歷史改成「可再套用」。

## 四、準備草稿與狀態轉移

`PreparationDraft` 保存 confirmed_loadout 的深拷貝、來源 profile_id／revision／rebirth_count、目前步驟、選中砲塔與驗證訊息；不寫磁碟。

1. `profile_menu → prepare_armor → prepare_weapons → prepare_deployment → prepare_confirm`。
2. 返回前一步保留草稿；取消整個準備丟棄草稿。無敵人、無 BattleState、無戰鬥時鐘。
3. 進入準備先把非法部署撤回庫存並顯示理由；缺空地武器的草稿要求玩家修正，不能偷偷免費配發額外商品。
4. 最終確認重新驗證所有權、輪次、槽位、容量及幾何，透過 confirm_loadout 保存成功後才建立 `BattleLoadout` 與新 AttemptId。
5. 保存失敗進 save_error；重試成功返回 prepare_confirm，由玩家再次開始，不自動建立戰鬥。期間任何新的購買、換檔、重生、配置修改都被阻擋。

`BattleLoadout` 為選中武器有效值、角色能力與部署塔定義／位置的不可變快照。戰鬥中不能購買或改造裝備；Profile 後續結算不反向改變飛行中的投射物。

當局初始持用槽為五槽中第一個非空位置，不能假設槽 1 必有武器；畫面位置仍保留使用者安排的空槽。

## 五、當局模型

| 型別 | 主要欄位 | 生命週期 |
| --- | --- | --- |
| `WeaponRuntime` | weapon_id、magazine_rounds、quota_remaining、next_shot_at、reload_finish_at、burst_remaining、next_burst_round_at、next_burst_start_at | 每把已攜帶武器一份，不按槽位重建；換關重置 |
| `TriggerState` | held、require_release、queued_commands | 暫停／失焦清除佇列並要求重新放開；不保存 |
| `ShotEvent` | attempt_id、sequence、shot_id、weapon_id／turret_instance_id、origin、endpoints、delivery、audio_key | 消費一次；霰彈子來源含 pellet_index |
| `ProjectileState` | id、attempt_id、source_id、weapon_id／turret_type_id、position、previous_position、direction、speed、damage、remaining_range、expires_at、target_id、turn_rate、hit_radius、blast_radius | 防空有 target_id，火箭沒有；命中或到期移除 |
| `CollisionHit` | distance、point、normal、kind、target_id、stable_order | 純規則查詢結果；同距離世界優先 |
| `DifficultySnapshot` | a、b、air_hp_factor、ground_hp_factor、speed_factor、turn_factor | 出生與空降共用本關快照 |
| `Aircraft` | 增加 max_hp、approach_duration、turn_rate、max_yaw_deflection、stable_order | 取消無名 tuple 的參數解讀 |
| `Enemy` | 增加有效 max_hp 與 stable_order | 不再以 kind 回推固定 3／10 |
| `TurretRuntime` | instance_id、turret_type_id、position、target_id、visible_since、next_shot_at | 只從確認部署建立；不減庫存 |
| `PendingSave` | candidate_profile、operation_id、result、return_route、continuation | 保存失敗時保留完整候選；成功後只執行一次路由恢復 |

火箭 quota_remaining 包含尚可發射的總發數；初始 W19=3、W20=5 且 magazine_rounds=1。發射同時減彈匣及總配額，換彈只把彈匣補為 min(1, quota_remaining)，不增加總配額。

## 六、重生與結算

- 重生候選先建立新輪免費裝備、空裝甲／塔庫存、零等級、預設配置與零金幣；保留 profile_id、歷史完成關卡、全部 operation_history，再增加 r、revision 並追加本次紀錄。
- 重生成功將 cursor 設 1-1，資格關閉；保存失敗保留完整重生候選但不允許繼續遊玩，不能只清掉一部分商品。
- 成功小關依既有公式發獎勵並推進 cursor；最終成功可再由 1-1 開始相同規模並保留資格。敗北的 failure 保存成功後將 cursor 設為 1-1；若保存失敗，先留在 save_error 並阻擋出戰，重試成功後才套用重設。重新載入檔案及重生仍回 1-1。
- reward／failure 的操作 ID 使用 AttemptId，僅 AppState 對自己持有且已結束的當局發出。重複 settle 不重複結算，舊 attempt 或舊輪次不能建立新資格。

詳細交易邊界、保存形狀及操作回傳見 [保存與交易契約](contracts/save-transactions.md)。
