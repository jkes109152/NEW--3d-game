# 任務：3D 防空守衛完整重建

**輸入**：`specs/001-air-defense-rebuild/` 下的 spec、plan、research、data-model、contracts、quickstart 與驗收矩陣

**前置文件**：`plan.md`、`spec.md`、`research.md`、`data-model.md`、`contracts/`、`quickstart.md`、`acceptance-matrix.md`

**測試策略**：規格明確要求 T01～T22，因此任務包含標準庫 `unittest`、固定亂數種子／時鐘、故障注入、引擎冒煙測試、實際輸入、截圖與效能驗收。

**任務格式**：每列必須是 `- [ ] T### [P?] [US#] 描述（含檔案路徑）`；`[P]` 只表示可與同階段其他任務平行；使用者故事階段必須帶 `[US#]`。

## 依賴與執行順序

```text
第 1 階段：設定
    ↓
第 2 階段：基礎建設
    ↓
US1 檔案／主選單／垂直切片 ──┬── US2 空地混合戰
                              ├── US3 武器／砲塔（依賴 US2 的戰鬥迴圈）
                              ├── US4 戰役／商店／重生（依賴 US1 的主選單）
                              ├── US5 保存／復原（可與 US2～US4 的純規則測試平行）
                              └── US6 HUD／音效／設定（依賴 US1～US3 的事件快照）
                                      ↓
                                  US7 啟動／效能／交付
                                      ↓
                                  品質優化與 converge
```

基礎建設完成前不得開始任何使用者故事。US2 的純規則敵人測試可在 US1 完成前進行，但實際垂直切片整合依賴 US1 的場景生命週期。US5 的存檔故障測試可與戰鬥開發平行；US6 的完整畫面驗收須等相關 HUD 事件存在。每一階段在檢查點執行該故事的獨立測試。

## 第 1 階段：設定（共用基礎）

**目的**：建立依賴、專案結構、測試入口與資產授權基礎。

- [X] T001 建立 `air_defense/`、`tests/`、`tests/fixtures/`、`assets/models/`、`assets/textures/`、`assets/audio/`、`assets/fonts/`、`docs/` 與 `artifacts/` 目錄，並在 `air_defense/__init__.py` 建立套件版本常數。
- [X] T002 [P] 建立 `requirements-game.txt`，固定 `ursina==8.3.0` 與 `panda3d==1.10.16`，註明只支援 Python 3.12.x 與可離線安裝的 wheel cache 行為。
- [X] T003 [P] 建立 `start_game.cmd`，依 `contracts/launcher.md` 從批次檔自身目錄解析路徑、只接受 Python 3.12.x、建立 `.venv`、安裝固定依賴並以 `python -m air_defense.main` 啟動。
- [X] T004 [P] 建立 `run_tests.cmd`，使用同一 `.venv` 執行 `compileall` 與 `unittest`，將測試保存根目錄隔離並傳回真實退出碼。
- [X] T005 [P] 建立繁體中文 `README.md`，記錄首次／後續啟動、操作、存檔位置、測試入口、離線限制與常見錯誤路徑。
- [X] T006 [P] 建立 `assets/LICENSES.md`，標記程序化模型、自合成 WAV 與自製字型／材質；預留外部資產的來源、版本與授權欄位。
- [X] T007 [P] 建立 `tests/__init__.py` 與 `tests/fixtures/__init__.py`，提供固定亂數種子、受控時鐘、暫存 Profile 根目錄、事件收集器與測試當局工廠。

## 第 2 階段：基礎建設（阻塞所有使用者故事）

**目的**：完成純規則、資料契約、事件管線與引擎適配骨架；此階段完成前不可實作故事 UI。

- [X] T008 建立 `air_defense/config.py`，集中定義世界座標、玩家／城市／飛機／敵兵／武器／砲塔數值、解析度、FPS 量測門檻與品質預設。
- [X] T009 [P] 在 `air_defense/entities.py` 建立 Aircraft、Enemy、Turret、Missile、Player、City 的不可變設定與可變狀態資料型別，包含穩定 ID、`phase` 與 `hit_envelope`。
- [X] T010 [P] 在 `air_defense/state.py` 建立 AppState、BattleState、CampaignCursor、受控 SimulationClock、attempt_id、固定 1/120 tick accumulator 與 pause／teardown 狀態機。
- [X] T011 在 `air_defense/progression.py` 實作 `roster_for`、a-b 驗證、LevelDefinition、boss_count、獎勵公式、下一關游標、升級目錄、升級效果公式與重生條件。
- [X] T012 在 `air_defense/save_data.py` 實作 Profile v1 封閉 schema、型別／範圍驗證、`profile_revision`、永久 `operation_history`、fingerprint 衝突判定與五欄位路徑解析。
- [X] T013 在 `air_defense/save_data.py` 實作同目錄暫存檔、flush、原子替換、損壞檔 bytes 備份、未知 schema 拒絕、`backup_failed` 與刪除確認的資料層 API。
- [X] T014 在 `air_defense/combat.py` 建立統一攻擊驗證器，依序檢查解鎖、階段、目標類型、存活、可見性、距離、冷卻、彈藥與鎖定，回傳可顯示的穩定錯誤碼。
- [X] T015 在 `air_defense/state.py` 實作固定 tick 事件順序：輸入／計時 → 飛機 → 敵兵 → 導彈 → 攻擊請求 → 命中／傷害 → 敵人攻擊 → 完成／失敗 → ID 排序清理；加入超過 8 tick 的診斷計數。
- [X] T016 [P] 在 `air_defense/scene.py` 建立 Ursina／Panda3D 初始化、相機、世界碰撞器（collider）、資產登錄表與無進階著色器（shader）的基本材質回退介面。
- [X] T017 [P] 在 `air_defense/ui.py` 建立 UI 根節點生命週期、畫面狀態路由、輸入焦點、繁中字型載入介面與 1280×720／1920×1080 的縮放計算骨架。
- [X] T018 [P] 在 `air_defense/audio.py` 建立音效事件匯流排、音量／靜音控制、同時播放上限與無音訊裝置的無聲回退。
- [X] T019 [P] 建立 `tests/test_progression.py`、`tests/test_save_data.py`、`tests/test_state.py` 與 `tests/test_contracts.py` 的測試骨架，確認測試可在無 Ursina 視窗時執行。
- [X] T020 執行基礎建設關卡：以 `run_tests.cmd` 通過 schema、交易、關卡公式、固定 tick 與契約冒煙測試，並把命令與退出碼記錄到 `artifacts/foundational.log`。

**檢查點**：規則核心可在無視窗環境建立當局、驗證交易、推進固定 tick、載入／保存 Profile，且所有任務文件與說明使用繁體中文。

## 第 3 階段：使用者故事 1－建立／載入檔案並開始戰役（P1，MVP 基礎）

**目標**：五欄位選擇 → 個人主選單 → 手動開始 1-1 → 返回主選單的流程可獨立操作。

**獨立測試**：在隔離 Profile root 建立空欄位，透過滑鼠選擇、進入主選單、開始 1-1、返回並重啟，確認摘要與下一關規則正確；取消刪除不得改變任何欄位。

### US1 測試

- [X] T021 [P] [US1] 在 `tests/test_profile_flow.py` 覆蓋五欄位隔離、空欄位建立、非空欄位摘要、刪除取消與重複確認。
- [X] T022 [P] [US1] 在 `tests/test_app_state.py` 覆蓋 `boot → slot_select → profile_menu → battle_setup`、完成後返回主選單與重啟回 1-1。
- [X] T023 [US1] 在 `tests/test_story1_vertical.py` 建立可控制的 1-1 垂直切片，驗證開始、當局建立、結果結算只執行一次並更新 Profile。

### US1 實作

- [X] T024 [US1] 在 `air_defense/save_data.py` 完成 SlotRepository 的列舉、摘要讀取、建立空檔、選定欄位與隔離刪除操作。
- [X] T025 [US1] 在 `air_defense/state.py` 完成 SlotSelectState、ProfileMenuState、BattleSetupState 與返回上一層的狀態轉移。
- [X] T026 [US1] 在 `air_defense/ui.py` 實作五個可點擊欄位、摘要卡、刪除二階段確認、開始／商店／設定／返回選檔／離開按鈕與鍵盤焦點。
- [X] T027 [US1] 在 `air_defense/scene.py` 建立最小 1-1 場景、玩家出生碰撞、目標大樓、道路、掩體與不掉出地圖的邊界 collider。
- [X] T028 [US1] 在 `air_defense/main.py` 組裝啟動、選檔、主選單、戰鬥建立、結果結算與清理，確保每次進出不重複註冊輸入或更新 task。
- [ ] T029 [US1] 在 `tests/test_story1_vertical.py` 接上真實 UI 事件介面，完成至少一輪滑鼠／鍵盤開始 1-1 的正常輸入冒煙測試，將截圖保存至 `artifacts/us1/`。

**檢查點**：玩家可獨立完成選檔、主選單與 1-1 入口；測試與畫面證據確認沒有自動連關、錯誤刪除或生命週期洩漏。

## 第 4 階段：使用者故事 2－空地混合戰（P1）

**目標**：飛機、下降敵兵、地面敵兵、城市與玩家威脅同時運作，並以掩體與固定路線提供公平碰撞。

**獨立測試**：固定 seed 產生兩架飛機；先擊落一架並觀察另一架持續接近，再於約 4 秒下降期間擊殺敵兵，最後完成或觸發三種失敗條件。

### US2 測試

- [X] T030 [P] [US2] 在 `tests/test_aircraft_rules.py` 覆蓋四種飛機資料、航線轉向、接近警告、撞城 swept 判定與被擊落一次性事件。
- [X] T031 [P] [US2] 在 `tests/test_enemy_lifecycle.py` 覆蓋下降 3.75～4.25 秒、來源批次、0 敵兵批次、空中擊殺、落地路線與城市攻擊區。
- [X] T032 [P] [US2] 在 `tests/test_world_collision.py` 建立玩家膠囊、人物 0.8×1.8×0.6 包絡、掩體遮擋、路線走廊與不可穿牆測試固定資料。
- [X] T033 [US2] 在 `tests/test_mixed_battle.py` 驗證 T05、T06、T11 的空地混合整合事件與玩家／城市／撞城立即失敗。

### US2 實作

- [X] T034 [US2] 在 `air_defense/entities.py` 實作四種 AircraftState 的路徑、機頭朝向、閃避振幅／頻率、最大偏航／俯仰與接近時間。
- [X] T035 [US2] 在 `air_defense/entities.py` 實作擊落後下降批次、降落傘／吊帶狀態、敵兵 0～3 抽樣、支援 6 名與 Boss 1 名來源關聯。
- [X] T036 [US2] 在 `air_defense/entities.py` 實作一般敵兵／地面 Boss 的掩體路線、掩護／推進角色、攻擊冷卻、落地 phase 與路線碰撞停止規則。
- [X] T037 [US2] 在 `air_defense/combat.py` 實作玩家 HP、城市 HP、敵人射擊、城市每秒 10 傷害、遮擋 raycast 與三種立即失敗原因。
- [X] T038 [US2] 在 `air_defense/state.py` 將飛機／敵兵／城市／玩家更新接入固定 tick，完成小關條件「所有飛機擊落且所有批次清除」的單次結算。
- [X] T039 [US2] 在 `air_defense/scene.py` 建立四種飛機、兩種敵兵、降落傘、目標大樓、道路、掩體與攻擊區的可辨識程序化模型及 collider。
- [X] T040 [US2] 在 `air_defense/ui.py` 加入空襲危險、飛機／下降／地面敵兵數、城市受襲與三種失敗原因的 HUD／結果提示。
- [ ] T041 [US2] 在 `tests/test_mixed_battle.py` 驗證實際雙機空地混合戰並將下降、完成與失敗截圖／事件日誌保存至 `artifacts/us2/`。

**檢查點**：US1 的入口與 US2 的混合戰可連續遊玩；T05、T06、T10、T11 與世界碰撞案例通過。

## 第 5 階段：使用者故事 3－五種武器與自動砲塔（P1）

**目標**：所有武器依目標、距離、可見性、冷卻與彈藥契約造成合法且至多一次的傷害。

**獨立測試**：對每種武器執行合法／非法目標、12／12.01、32／32.01、180、遮擋、冷卻與彈藥測試；以 12 架飛機驗證多目標齊射。

### US3 測試

- [X] T042 [P] [US3] 在 `tests/test_weapon_validation.py` 覆蓋五槽位、解鎖、目標類型、射程邊界、遮擋、冷卻與非法操作不改狀態。
- [X] T043 [P] [US3] 在 `tests/test_lock_and_missiles.py` 覆蓋單目標 3 秒鎖定、離框 0.375 秒保留 45%～55%、0.75 秒歸零、換目標、導彈 target_id、轉向、掃掠與命中優先。
- [X] T044 [P] [US3] 在 `tests/test_multi_lock.py` 覆蓋 12 架獨立進度、全滿齊射、空集合／部分完成／失效目標拒射與一次冷卻。
- [X] T045 [P] [US3] 在 `tests/test_rpg_turrets.py` 覆蓋 RPG 半徑去重、下降敵兵、飛機排除、三發資源、砲塔最多六台與 Boss 最低血量。
- [X] T046 [US3] 在 `tests/test_weapon_integration.py` 驗證 T07～T14、T21 的切槍、命中事件、粒子／曳光不重複扣血與最後敵人結算。

### US3 實作

- [X] T047 [US3] 在 `air_defense/combat.py` 完成五種武器的 attack request、射線起點、水平／三維距離規則與統一錯誤碼。
- [X] T048 [US3] 在 `air_defense/combat.py` 完成單目標／多目標 LockState、白框倍率、輔助瞄準每秒 3 度上限與新版／舊版共用進度。
- [X] T049 [US3] 在 `air_defense/entities.py` 完成 MissileState 的有限轉向、線段掃掠、固定目標、命中半徑／壽命與回收池。
- [X] T050 [US3] 在 `air_defense/combat.py` 完成 RPG 爆炸中心、半徑 6 去重、35 傷害、三發資源與投射物只作視覺回饋。
- [X] T051 [US3] 在 `air_defense/entities.py` 完成 TurretState 的固定位置、最近目標穩定 ID、0.20 秒冷卻、32 射程、六台上限與 Boss 最低血量。
- [X] T052 [US3] 在 `air_defense/ui.py` 與 `air_defense/scene.py` 完成五種第一人稱武器模型、準心／狙擊鏡／防空框互斥、後座與命中特效。
- [X] T053 [US3] 在 `air_defense/audio.py` 接入武器射擊、鎖定、導彈、命中、爆炸與砲塔事件，套用同時播放上限。
- [ ] T054 [US3] 在 `tests/test_weapon_integration.py` 執行實際多目標齊射與狙擊／手槍／RPG／砲塔命中，將畫面與導彈 target_id 日誌保存至 `artifacts/us3/`。

**檢查點**：US2 混合戰可使用全部已解鎖武器；T07～T14、T21 通過，且沒有固定多目標容量或重複傷害。

## 第 6 階段：使用者故事 4－戰役、商店與重生（P1）

**目標**：完成 a-b 進度、金幣、十項升級、失敗／最終關重生資格與冪等交易。

**獨立測試**：使用隔離 Profile 完成 A=2 七關，核對編隊與獎勵；執行成功／失敗／缺錢／重複 operation_id 的商店與重生流程。

### US4 測試

- [X] T055 [P] [US4] 在 `tests/test_campaign_progression.py` 覆蓋 T01～T04、A=2／3／4／5／19、無效 a-b、下一關與最終關。
- [X] T056 [P] [US4] 在 `tests/test_economy.py` 覆蓋 T03、T16、T17 的獎勵、十項升級、前置、價格、上限、缺錢與重生費用。
- [X] T057 [P] [US4] 在 `tests/test_transaction_idempotency.py` 覆蓋 purchase／reward／rebirth 的相同 fingerprint 重試與衝突 fingerprint 拒絕。
- [X] T058 [US4] 在 `tests/test_campaign_integration.py` 驗證 A=2 七關、金幣累積、至少一項升級、死亡、重生後 A=3／金幣 0／永久資料保留。

### US4 實作

- [X] T059 [US4] 在 `air_defense/progression.py` 完成標準「特」固定對應支援飛機、快速飛機獨立測試遭遇、獎勵與同次執行下一關游標。
- [X] T060 [US4] 在 `air_defense/progression.py` 完成十項商店目錄的顯示名稱、價格、上限、前置、效果公式與錯誤結果。
- [X] T061 [US4] 在 `air_defense/save_data.py` 完成購買／獎勵／重生的 `operation_history` 提交、`profile_revision`、重試與保存失敗保留。
- [X] T062 [US4] 在 `air_defense/state.py` 完成成功結算、失敗結算、資格開放、主動結束不給獎勵與重生後回 1-1 的流程。
- [X] T063 [US4] 在 `air_defense/ui.py` 完成十項商店主列、效果說明、`1..9,0` 快捷鍵、重生條件／費用／全額歸零確認與結果提示。
- [ ] T064 [US4] 在 `tests/test_campaign_integration.py` 執行完整 A=2 正常／失敗／重生流程，保存金幣與主選單截圖至 `artifacts/us4/`。

**檢查點**：玩家可完成首次戰役、購買與自願重生；T01～T04、T16、T17、T20 通過。

## 第 7 階段：使用者故事 5－保存、復原與跨次啟動（P2）

**目標**：五欄位、原子保存、壞檔復原、刪除確認與跨重啟冪等交易可靠運作。

**獨立測試**：以暫存 Profile 根目錄模擬缺檔、壞 JSON、未知 schema、備份／寫入中斷、五欄位交錯與舊 operation 回呼。

### US5 測試

- [X] T065 [P] [US5] 在 `tests/test_save_recovery.py` 覆蓋 T18、T19 的缺檔、封閉 schema、未知版本、負值／錯型別、原始 bytes 備份與原子替換。
- [X] T066 [P] [US5] 在 `tests/test_save_transactions.py` 覆蓋 T20 的保存失敗、`backup_failed`、重試不重扣、衝突 operation 與 profile revision。
- [X] T067 [P] [US5] 在 `tests/test_slot_isolation.py` 覆蓋五欄位同時資料、刪除取消／確認、備份歸屬與其他欄位不受影響。
- [X] T068 [US5] 在 `tests/test_restart_persistence.py` 模擬程式重啟，確認永久資料保留而當局 HP、敵人、導彈、彈藥、冷卻與鎖定重新建立。

### US5 實作

- [X] T069 [US5] 在 `air_defense/save_data.py` 補齊 `SaveError` 分類、繁中錯誤訊息、`slot-N.corrupt.YYYYMMDDTHHMMSSZ.json` 備份與復原確認結果。
- [X] T070 [US5] 在 `air_defense/save_data.py` 加入單執行緒序列化讀寫、暫存檔清理、並行讀取只看完整舊／新檔與檔案權限錯誤回退。
- [X] T071 [US5] 在 `air_defense/ui.py` 完成保存錯誤、重試、壞檔備份、重建與刪除兩階段確認畫面，避免跨畫面 mutation event。
- [ ] T072 [US5] 在 `tests/test_save_recovery.py` 執行故障注入並將原始位元組、備份路徑、重試結果與退出碼保存至 `artifacts/us5/`。

**檢查點**：T18～T20 通過；保存失敗不會假稱成功、重試不重複交易，正式 Profile 與測試 Profile 完全隔離。

## 第 8 階段：使用者故事 6－HUD、音效、設定與畫面品質（P2）

**目標**：完成繁中 HUD／選單、兩種瞄準模式、音效、資產回退、暫停／失焦與指定解析度設定。

**獨立測試**：以 1280×720 與 1920×1080、視窗／全螢幕、中文路徑走過存檔、主選單、商店、戰鬥、暫停、結果與設定。

### US6 測試

- [X] T073 [P] [US6] 在 `tests/test_ui_state.py` 覆蓋畫面狀態、按鍵優先順序、準心互斥、文字提示去重與商店滑鼠／快捷鍵同 ID。
- [X] T074 [P] [US6] 在 `tests/test_settings.py` 覆蓋瞄準模式同次執行保留、音量／靈敏度／畫質／全螢幕／降低動態效果設定與無效值回退。
- [X] T075 [P] [US6] 在 `tests/test_audio_assets.py` 覆蓋音效事件上限、無裝置靜音回退、資產登錄表缺檔回退與材質實例隔離。
- [X] T076 [US6] 在 `tests/test_pause_focus.py` 驗證 T21、T22 的暫停／失焦停止所有計時、恢復不補算、切槍不重設 CD／彈藥與清理回呼。

### US6 實作

- [X] T077 [US6] 在 `air_defense/ui.py` 完成戰鬥 HUD：玩家／城市 HP、鎧甲、回血、警報、A-B、敵人剩餘、五槽位、CD、RPG 彈藥、金幣與 r／A。
- [X] T078 [US6] 在 `air_defense/ui.py` 完成普通炮新版／舊版鎖定、多目標動態準心、狙擊鏡、一般／RPG 準心的互斥與 0.21 UI 座標縮放。
- [X] T079 [US6] 在 `air_defense/ui.py` 完成 settings.json、滑鼠靈敏度、主／音效音量、畫質、全螢幕與降低動態效果的實際套用。
- [X] T080 [US6] 在 `air_defense/state.py` 與 `air_defense/main.py` 完成 Esc 暫停、失焦自動暫停、滑鼠釋放、恢復 accumulator 清零與結束本局回 1-1。
- [X] T081 [US6] 在 `air_defense/scene.py` 完成暖色方向光、環境填光、陰影／霧、程序化四種飛機、人物／Boss、武器、城市、道路、掩體、粒子與有限壽命特效。
- [X] T082 [US6] 在 `assets/fonts/` 放入可隨包提供且授權清楚的繁中字型，在 `assets/LICENSES.md` 登記來源，並在 `air_defense/scene.py` 驗證字型載入與缺字診斷。
- [X] T083 [US6] 在 `air_defense/audio.py` 完成所有音效事件、自合成／自製 WAV、匯流排音量、播放上限、鎖定提示與無聲回退。
- [ ] T084 [US6] 在 `tests/test_ui_state.py` 執行兩種解析度與設定冒煙測試，將存檔、主選單、HUD、鎖定、商店、暫停與結果截圖保存至 `artifacts/us6/`。

**檢查點**：T21、T22 與指定解析度畫面驗收通過；所有新增／修改 SDD 與交付說明通過繁體中文檢查。

## 第 9 階段：使用者故事 7－啟動、測試與交付（P3）

**目標**：乾淨路徑可雙擊啟動、同環境可測試，並交付可核查的文件、截圖、效能與清理證據。

**獨立測試**：在含空白／中文的全新路徑執行 `start_game.cmd`、`run_tests.cmd`，模擬缺 Python、無網路、缺音訊／著色器（shader）／外部模型與錯誤退出碼。

### US7 測試

- [ ] T085 [P] [US7] 在 `tests/test_launcher_contract.py` 以臨時複製路徑驗證 `start_game.cmd`／`run_tests.cmd` 的路徑解析、Python 檢查、退出碼、日誌與正式存檔隔離。
- [X] T086 [P] [US7] 在 `tests/test_lifecycle_metrics.py` 驗證十次開始／結束的活動實體（`entities`）、排程回呼、導彈（`missiles`）、特效（`effects`）與輸入處理器回到基準值。
- [ ] T087 [US7] 建立 `tools/performance_probe.py` 與 `tests/test_performance_scenarios.py`，實作暖機 10 秒、A=4 量測 60 秒、A=8 壓力場景量測 60 秒且每秒取樣、平均 FPS、P1（最差 1%）frame time 對應 FPS、連續兩個以上超過 250 ms 的 frame time 卡頓、硬體／解析度／畫質與十次生命週期基準差異的輸出，驗證平均 FPS 至少 55、P1 對應 FPS 至少 45、壓力場景活動計數不呈單調增加且不違反卡頓門檻，並確認不以限制 A 或鎖定數作弊。

### US7 實作

- [ ] T088 [US7] 完成 `start_game.cmd` 的 Python 3.12.x 偵測、`.venv` 建立、依賴摘要／快取檢查、離線後續啟動與錯誤視窗停留。
- [ ] T089 [US7] 完成 `run_tests.cmd` 的語法檢查、完整 `unittest`、隔離 Profile、日誌保存與真實退出碼傳遞。
- [ ] T090 [US7] 在 `docs/SPEC.md`、`docs/PLAN.md`、`docs/TASKS.md` 與 `docs/DECISIONS.md` 同步最終規格、計畫、任務、決策與技術取捨，全部使用繁體中文說明。
- [ ] T091 [US7] 在 `docs/ACCEPTANCE.md` 逐項填寫 T01～T22 的實際命令、退出碼、測試 Profile、截圖／日誌／FPS 路徑與未完成限制。
- [ ] T092 [US7] 在 `artifacts/` 保存 1280×720／1920×1080、A=4／A=8、十次生命週期、缺能力回退與啟動器驗證結果，並產生交付檔案清單。
- [ ] T093 [US7] 建立並執行 `tools/package_project.ps1` 產生可攜 ZIP 清單，排除 `.venv`、快取、玩家存檔、`.git`、秘密與不相關檔案，並驗證新路徑可重建環境。

**檢查點**：US7 的啟動、測試、效能、清理、文件、截圖與交付包均有真實證據；不能將未執行項目標示為通過。

## 第 10 階段：品質優化與跨切面收尾

**目的**：在所有故事通過後處理效能、文件一致性、授權、回歸與 converge。

- [ ] T094 [P] 在 `air_defense/scene.py` 與 `air_defense/entities.py` 依實測結果加入導彈／特效物件池、共享幾何、距離簡化與查詢快取，不改變 A 或多目標鎖定契約。
- [ ] T095 [P] 在 `README.md`、`docs/ACCEPTANCE.md` 與 `assets/LICENSES.md` 做最後繁體中文、路徑、授權與交付清單檢查。
- [ ] T096 [P] 在 `tests/` 執行完整回歸、語法檢查、T01～T22 與無視窗回退；將最終退出碼保存至 `artifacts/final-tests.log`。
- [ ] T097 執行 `quickstart.md` 的首次啟動、垂直切片、解析度、效能與十次生命週期流程，更新 `docs/ACCEPTANCE.md` 的實測結果。
- [ ] T098 執行 `$speckit-converge` 對照 spec、plan、tasks、程式與證據；若有差異，先在 `specs/001-air-defense-rebuild/tasks.md` 增加具體任務，再重新執行受影響驗收。
- [ ] T099 確認 `.gitignore` 排除 `.venv/`、`.tools/` 快取、玩家存檔與測試輸出中不應提交的檔案，並在 `C:\Users\lamuness\Desktop\game` 的本機倉庫檢查交付狀態。

## 平行執行機會

### 設定與基礎建設

- T002、T003、T004、T005、T006、T007 可在 T001 後分開處理。
- T009、T010、T016、T017、T018、T019 可在 T008 的數值契約完成後平行進行；T011～T015 依資料型別與事件順序銜接。

### 使用者故事

- US2 的 T030～T032、US3 的 T042～T045、US4 的 T055～T057、US5 的 T065～T067 可在基礎建設完成後由不同工作者平行執行。
- US6 的 T073～T075 可在 UI／音訊契約穩定後平行；T077～T083 會共享 `ui.py`、`scene.py` 與 `audio.py`，需避免同檔同時修改。
- US7 的 T085～T087 可與 US7 實作的文件整理平行，但正式效能與啟動器證據需等功能完成。

## 建議 MVP 與增量策略

### MVP

MVP 不只包含檔案選擇畫面；必須完成第 1 階段、第 2 階段、US1，以及 US2 的最小普通飛機 → 單目標鎖定／導彈 → 敵兵下降 → 手槍清除 → 結算垂直切片（T021～T029、T033～T041 的必要子集）。完成後先以正常滑鼠／鍵盤輸入驗證，再擴充所有武器與完整戰役。

### 增量交付

1. 設定 + 基礎建設：規則、保存、固定 tick、事件與測試可獨立運作。
2. US1 + US2 垂直切片：可開始並完成 1-1，形成第一個可玩版本。
3. US3：加入全部武器、鎖定、導彈、RPG、砲塔與合法命中。
4. US4：加入完整 a-b、商店、獎勵與重生。
5. US5 + US6：完成跨次資料安全、HUD、音效、設定與畫面品質。
6. US7 + 品質優化：完成可攜啟動、效能、截圖、文件、交付包與 converge。

### 每個任務完成的最低條件

- 任務列的檔案路徑實際存在且變更可由對應測試／畫面／日誌驗證。
- 受影響的 T 編號重新執行並保留真實退出碼；失敗不得勾選完成。
- 新增或修改的 SDD／docs 文字通過繁體中文檢查。
- 故障、缺能力或未驗證項目保留可重現證據與明確限制，不以假成功交付。
