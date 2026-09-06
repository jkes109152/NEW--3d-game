# 3D 防空守衛資料模型與狀態轉移

本文件把 [spec.md](spec.md) 的公開行為轉成可由純規則模組與場景適配層共同使用的資料契約。除 `玩家檔案` 與 `設定` 外，其他模型都是當局或畫面生命週期資料，不得直接寫入正式存檔。

## 持久資料

### 玩家檔案 `ProfileData`

| 欄位 | 型別 | 驗證／語意 |
|---|---|---|
| `schema_version` | 正整數 | 目前為 `1`；未知版本拒絕載入並保留原始位元組 |
| `coins` | 非負整數 | 只由成功交易或完整小關獎勵改變 |
| `rebirth_count` | 非負整數 | `A = 2 + rebirth_count`，載入時重新推導 |
| `upgrade_levels` | `map<UpgradeId, non-negative int>` | 只接受升級目錄中的 ID 與其動態上限 |
| `upgrade_caps` | map | 顯示用快照；載入時依 `rebirth_count` 與目錄重新推導，不能限制有效等級 |
| `unlocked_weapons` | 唯一字串集合 | 初始為 `ANTI_AIRCRAFT`, `SNIPER`, `PISTOL`；只能由解鎖交易加入 RPG／多目標炮 |
| `rebirth_available` | bool | 失敗或完成當前 A 的最終小關後為真；成功重生後為假 |
| `last_completed_a_b` | `null` 或 `{a:int,b:int}` | 歷史摘要；重啟後戰役仍由 `1-1` 開始 |

| `profile_revision` | 非負整數 | 每次成功套用 Profile 變更遞增；只用於交易結果比對 |
| `operation_history` | `list<OperationEntry>` | 跨重啟冪等記錄；v1 不淘汰，避免重送舊 ID 重新套用 |

禁止保存玩家當前 HP、城市 HP、敵人、飛機、導彈、砲塔、冷卻、彈藥、鎖定、未完成關卡或活動回呼。

### 設定 `Settings`

設定與永久 Profile 分離。欄位包含 `aim_mode`（`modern`／`legacy`）、主音量、音效音量、滑鼠靈敏度、畫質預設、全螢幕／視窗、降低動態效果。防空瞄準模式預設 `modern`，在同次執行中保留，關閉遊戲後重設；其他品質設定可由獨立 `settings.json` 保存。

## 戰役與關卡

### 戰役游標 `CampaignCursor`

| 欄位 | 型別 | 驗證／語意 |
|---|---|---|
| `A` | 整數 | `A >= 2`，由 `2 + rebirth_count` 推導 |
| `next_a`, `next_b` | 整數 | 初始 `1,1`；同次執行完成小關後指向下一關；重啟永遠重設 `1,1` |
| `is_final_level` | bool | `a == A and b == 2*a + 1` |

有效 b 範圍為 `1..a+1`（`a < A`）或 `1..2a+1`（`a == A`）。`roster_for(a,b,A)` 的結果：

- `b <= a+1`：`b-1` 架人力支援飛機加上 `a-(b-1)` 架普通飛機；
- `b > a+1`：`b-(a+1)` 架裝甲 Boss 飛機加上其餘人力支援飛機。

### 小關定義 `LevelDefinition`

由 `(A,a,b,rebirth_count)` 純函式產生，包含 `level_id`、飛機編隊順序、`boss_count`、獎勵快照與是否最終關。獎勵為：

```text
floor((100 + 25*a + 10*(b-1) + 150*boss_count) * (1 + 0.5*rebirth_count))
```

產生器不得為無效 `(A,a,b)` 建立部分結果。

## 當局模型

### `BattleState`

`BattleState` 是一局小關唯一的可變狀態來源，至少包含：

- `attempt_id`、`phase`（`setup`／`active`／`paused`／`success`／`failure`／`teardown`）與受控模擬時鐘；
- `level`、玩家、城市、飛機／敵兵／砲塔／導彈的 ID map；
- 當局武器冷卻、RPG 彈藥、瞄準模式、鎖定狀態、回血計時與已用回血額度；
- 本局一次性事件集合（已結算獎勵、已處理死亡、已建立下降批次、已處理 operation）。

所有更新依序執行：輸入採樣 → 固定時間步 → 飛機／敵兵／導彈移動 → 合法命中與傷害 → 完成／失敗判定 → 清理 → HUD／渲染事件。`paused` 時固定時間步為零。

### 玩家 `PlayerState`

欄位包含位置、水平／垂直視角、`hp`、`max_hp = 100 + 10*max_hp_level`、`armor_level`、目前武器、每武器冷卻、RPG 剩餘彈藥、受傷時間、回血額度與瞄準狀態。正傷害為 `max(1, raw_damage - armor_level)`；五秒未受傷後每秒回 2，整關最多回有效最大 HP 的 20%。

### 城市 `CityState`

`hp` 初始 100，攻擊區中心固定於 `(0,0,-45)`，半徑基準 10。已落地敵兵進入攻擊區後每秒造成 10；城市傷害不受玩家鎧甲影響。`hp <= 0` 立即將當局轉為 `failure`。

### 飛機 `AircraftState`

| 欄位 | 說明 |
|---|---|
| `id` | 當局唯一、導彈使用的固定 target_id |
| `kind` | `NORMAL`／`MANPOWER_SUPPORT`／`FAST`／`ARMORED_BOSS` |
| `hp`, `max_hp` | 普通／支援／快速為 1，Boss 為 5 |
| `position`, `rotation` | 世界座標與機頭朝向；移動沿機頭方向並受最大轉向限制 |
| `flight_elapsed`, `flight_duration` | 26／34／16／38 秒基準 |
| `status` | `approaching`／`destroyed`／`impact` |
| `drop_batch_id` | 擊落後一次建立；無敵兵批次可為空 |

飛機擊落事件只處理一次；`impact` 不算擊落且立即失敗。快速飛機保留在模型與測試遭遇中，標準「特」固定對應支援飛機。

### 敵兵 `EnemyState`

| 欄位 | 說明 |
|---|---|
| `id`, `source_batch_id` | 唯一 ID 與來源飛機批次 |
| `kind` | `NORMAL` 或 `GROUND_BOSS` |
| `phase` | `descending`（約 4 秒）／`ground`／`dead` |
| `hp`, `max_hp` | 普通 3、Boss 10 |
| `position`, `route_index`, `role` | 掩體路線位置、路線節點與掩護／推進角色 |
| `attack_cooldown`, `city_attack_active` | 已落地才可攻擊玩家或城市 |

下降中的敵兵可被玩家地面武器命中，但不可被砲塔或敵兵 AI 攻擊；落地後沿固定掩體路線平順前進，路線碰撞不得穿牆。

### 砲塔 `TurretState`

每台包含固定位置、穩定 ID、目前 `target_id`、冷卻與啟用狀態。解鎖後每關建立 1 台，容量每級增加 1，總數最多 6；射程 32（含邊界）、傷害 1、冷卻 0.20 秒、無限彈藥，只接受已落地敵兵。砲塔對 Boss 的共同傷害下限為 Boss 最大 HP 的 50%（HP 10 時至少保留 5）。

### 導彈 `MissileState`

每枚保存 `id`、來源武器、`target_id`、位置、速度向量、年齡與剩餘壽命。速度 90／秒、最大轉向 240 度／秒、命中半徑 1.5、壽命 5 秒；使用上一位置到下一位置的線段掃掠。目標死亡、消失、命中、過期或當局結束時回收，永不改追別的飛機。

## 瞄準與武器

### `LockState`

單目標模式保存目前 target ID、進度、白框有效性、可見性與衰減狀態；多目標模式保存 `map<aircraft_id, progress>`，每個目標獨立累積。基準鎖定時間 3.0 秒，離框後以完整進度 0.75 秒線性歸零；關閉瞄準、換武器、死亡或關卡結束清除。多目標炮沒有容量欄位，白框為普通炮的 2 倍並共用白框升級。

### `WeaponDefinition` 與合法攻擊

武器目錄固定定義目標類型、解鎖 ID、冷卻、傷害、射程與資源：

| 武器 | 目標 | 冷卻 | 傷害／資源 |
|---|---|---:|---|
| 單目標防空炮 | 可見、入框、已鎖定飛機 | 1.25 秒 | 每枚導彈 1，無限 |
| 狙擊槍 | 下降／地面敵兵或 Boss | 0.75 秒 | 1，無限，射程 180 |
| 手槍 | 下降／地面敵兵或 Boss | 0.20 秒 | 1，無限，射程 12 |
| RPG | 下降／地面敵兵或 Boss | 2.5 秒 | 35，半徑 6，每關 3 發，射程 12 |
| 多目標防空炮 | 框內全部有效飛機 | 1.25 秒 | 每目標一枚導彈，水平距離 180 |

每次攻擊先驗證解鎖、階段、目標類型、存活、可見性、距離、冷卻、彈藥與必要鎖定；失敗返回原因且不改變狀態。地面武器使用鏡頭中心射線與敵人包絡；RPG 使用敵人中心的三維距離；多目標炮使用玩家到飛機中心的水平距離。

## 商店與交易

### `UpgradeDefinition`

商店目錄固定 10 個 ID，包含顯示順序、名稱、基價、重複上限、前置與效果：`max_hp`（250）、`armor`（350）、`aa_lock_time`（300）、`aa_whitebox`（250）、`aa_aim_assist`（750，一次）、`weapon_cooldown`（300）、`rpg`（500，一次）、`auto_defense`（600，一次）、`auto_defense_capacity`（450，最多 5 級且需先解鎖砲塔）、`multi_anti_aircraft`（750，一次）。重複升級費用為 `base_cost * (current_level + 1)`；容量與所有上限依 r 動態推導。

### `OperationRecord` 與交易狀態

每次購買、重生、獎勵與保存使用唯一 `operation_id`；狀態為 `pending`／`applied`／`rejected`／`failed_retryable`。Profile v1 的 `operation_history` 每筆 `OperationEntry` 包含：`operation_id`、`kind`、要求 fingerprint、結果碼、套用後 `profile_revision` 與變更摘要。相同 ID 且 fingerprint 相同時回傳第一次結果；相同 ID 但 fingerprint 不同時回傳 `operation_conflict`，兩者都不改資料。`operation_history` 與 Profile 一起以同一個暫存檔原子提交，不設淘汰上限。保存失敗保留待保存結果與重試狀態。

## 完整升級目錄

| ID | 上限 | 前置 | 每級效果 |
|---|---:|---|---|
| `max_hp` | `5+r` | 無 | 最大 HP `100+10L`；基價 250 |
| `armor` | `3+r` | 無 | 正傷害減 L、最少扣 1；基價 350 |
| `aa_lock_time` | `5+r` | 無 | 鎖定時間 `max(0.1,3-0.15L)` 秒；基價 300 |
| `aa_whitebox` | `5+r` | 無 | 白框倍率 `1+0.10L`，同時影響兩種防空炮；基價 250 |
| `aa_aim_assist` | 一次 | 無 | 僅開鏡時每秒最多修正 3 度；基價 750 |
| `weapon_cooldown` | `5+r` | 無 | 所有武器與砲塔 CD 乘 `max(0.50,1-0.05L)`；基價 300 |
| `rpg` | 一次 | 無 | 解鎖槽位 4；基價 500 |
| `auto_defense` | 一次 | 無 | 每關建立第一台砲塔；基價 600 |
| `auto_defense_capacity` | 5 | 先解鎖 `auto_defense` | 每級增加一台，總數最多 6；基價 450 |
| `multi_anti_aircraft` | 一次 | 無 | 解鎖槽位 5，動態全目標鎖定；基價 750 |

重複升級價格為 `base_cost * (current_level + 1)`。商店 UI 與快捷鍵都由同一目錄依固定順序 `1..9,0` 取得；`maxed`、`locked`、`prerequisite_missing`、`insufficient_coins`、`invalid_id` 都在扣款前拒絕。

## 世界碰撞與路線測試固定資料

- 座標基準為 `+Y` 向上、`+Z` 為模型前方；玩家速度 6、跳躍高度 1.5、重力採控制器 1.0 尺度；玩家 collider 為半徑 0.45、高 1.8 的膠囊近似。
- 敵兵路點固定為 `(-16,0,68) → (15,0,45) → (-14,0,20) → (13,0,-4) → (-10,0,-27) → (0,0,-45)`；路線生成的可通行走廊與靜態掩體 box 在載入時驗證不相交，敵兵沿線段平順移動，不能穿牆或瞬移。
- 飛機從 `(0,32,210)` 接近 `(0,10,-60)`，編隊水平間隔基準 10；每次更新先依機頭速度／轉向更新，再以 swept segment 與目標大樓 collider 或中心 `(0,10,-60)` 半徑 10 攻擊球檢查撞城。
- 玩家射線起點為相機中心，先命中世界遮擋 collider，再解析目標子模型的穩定 ID；人物瞄準包絡為中心對齊的 `0.8×1.8×0.6` box。防空炮仍使用可見／入框／鎖定契約，不以地面武器射程取代。

## 固定步事件契約

每幀將原始 dt 限制在 `[0,0.1]`，加入 accumulator；每幀最多執行 8 個 `1/120` 秒 tick，超過部分丟棄並增加診斷計數。每 tick 的決定順序為：

1. 佇列輸入與冷卻／回血計時；
2. 飛機移動、撞城判定與擊落後批次建立；
3. 敵兵下降、路線移動與 AI；
4. 導彈移動與 swept collision；
5. 玩家與砲塔攻擊請求；
6. 依穩定事件序列套用命中／傷害；
7. 敵兵對玩家／城市的攻擊；
8. 完成／失敗判定；
9. 依 ID 排序清理死亡、過期與終局物件。

同 tick 導彈命中與壽命到期時命中優先；同一來源對同一目標每 tick 至多結算一次。亂數只由 `Seed(attempt_id, level_id)` 的固定子流以穩定 ID 順序消耗。暫停時 accumulator 清零且不執行 tick；恢復不補算停留時間。

## 狀態轉移

### 應用流程

```text
boot → slot_select → profile_menu
  → battle_setup → active_battle ↔ paused
  → success_settlement / failure_settlement
  → profile_menu → next battle_setup
profile_menu → store / rebirth_confirm / settings / slot_select / exit
```

選檔刪除為 `delete_requested → delete_confirmed → empty_slot`；取消或跨畫面輸入回到原狀態。

### 戰鬥流程

```text
setup → active
active → paused → active
active → success   (所有飛機擊落且所有下降／地面敵兵清除)
active → failure   (玩家 HP=0、城市 HP=0 或飛機撞城)
success/failure → teardown → settlement → profile_menu
```

`success` 與 `failure` 是終端狀態；任何延遲回呼都必須帶 `attempt_id` 並在 `teardown` 後拒絕。
