# 任務：糖果風防空守衛與裝備成長改版

**輸入**：[規格](spec.md)、[計畫](plan.md)、[數值表](balance.md)、[研究](research.md)、[資料模型](data-model.md)、[快速驗證](quickstart.md)。
**契約**：[保存交易](contracts/save-transactions.md)、[戰鬥模擬](contracts/combat-simulation.md)、[介面部署](contracts/ui-deployment.md)、[呈現驗證](contracts/presentation-validation.md)。
**分支**：`002-gameplay-expansion`　**憲章**：1.4.0　**日期**：2026-09-06。
**狀態**：實作與驗收進行中；勾選代表已有實作及對應證據。既有 82 項基準不代表新版驗收。

## 格式與執行約定

- 每項使用 `- [ ] Tnnn [P?] [USn?] 說明與檔案路徑`；路徑相對專案根目錄 `C:/Users/lamuness/Desktop/game`。新檔案在所屬任務建立。
- `[P]` 僅標同階段可同時撰寫的獨立測試檔；須先完成該階段的前置工作。未標記任務依序執行，共用 state／UI／combat 等檔案不能併行修改。
- 測試依規格驗收與憲章 III 明確要求列入。各階段先寫行為／邊界測試，確認預期行為尚未達成，再實作使其通過；匯入錯誤本身不是有效的行為失敗證據。
- 商品及公式以 balance.md 為準；文件不由執行時解析，不另猜數值。資料形狀、十二交易、模擬順序、部署邊界及模型配方依上述契約。
- 本功能證據統一放 `artifacts/002-gameplay-expansion/`；保留歷史 001 證據與舊版存檔。必要真實畫面／輸入能力不可用時，記錄未驗證，不以 probe 冒充。
- 每個故事測試使用合法隔離資料及公開入口，可獨立重跑；獨立驗收不表示程式整合沒有前置依賴。共用模組在後續故事漸進補齊，禁止以假成功填入未完成行為。

## 階段 1：環境與驗證準備

**目標**：沿用既有專案，建立不接觸正式資料的新版驗證入口。

- [X] T001 核對目前分支為 002-gameplay-expansion、功能指標與憲章 1.4.0，將實際基準 SHA、Python／依賴版本及未提交變更範圍記錄於 `artifacts/002-gameplay-expansion/baseline.md`；GitHub 查詢只用 gh。
- [X] T002 在 `tests/fixtures/expansion.py` 建立可注入 ID／時間、臨時 LOCALAPPDATA、新舊分離根目錄及合法 v2 測試資料工廠；預期數值直接引用定案案例，不呼叫待測公式生成答案。
- [X] T003 更新 `tools/test_runner.py` 使用臨時 AIR_DEFENSE_V2_SAVE_DIR、保留真實退出碼，將本功能測試日誌另存 `artifacts/002-gameplay-expansion/tests.log` 並保留既有入口相容性。

**關卡**：隔離資料與驗證入口備妥，才開始共用基礎。

## 階段 2：共用基礎（阻擋所有故事）

**目標**：完成商品、保存、交易與世界查詢共用契約；故事專屬交易效果在所屬階段完成。

**獨立驗收**：純規則不匯入引擎；新 Profile 可嚴格往返保存；同操作重播、衝突與寫入失敗不重複套用。

### 先建立驗證

- [X] T004 [P] 在 `tests/test_catalog.py` 建立 20／6／3 數量、分類分配、免費 W01/W17/W03、固定價格與升級公式範例測試。
- [X] T005 [P] 在 `tests/test_profile_v2.py` 建立封閉 13 欄位、巢狀所有權、有限數值、未知版本、重複 key 與新舊根目錄隔離測試。
- [X] T006 [P] 在 `tests/test_transaction_v2.py` 建立請求封閉形狀、profile／輪次、同 ID 同指紋重播、異指紋衝突及 rejected revision 測試；明確斷言 result_code 與 reason 分開，結構／身分／未來輪次拒絕不記歷史，業務及舊輪次拒絕只記一次。

### 實作與整合

- [X] T007 新增 `air_defense/catalog.py`，依 balance.md 全表定義 frozen 商品、六種模式、七配件、顏色／圖樣、升級價格及適用性；移除 `air_defense/config.py` 作為另一份商品數值來源的責任。
- [X] T008 在 `air_defense/progression.py` 建立 Profile v2／OwnedWeapon／OwnedTurret 型別及 new_profile，深拷貝三免費武器與五槽初值，保留完整操作歷史。
- [X] T009 在 `air_defense/save_data.py` 實作 v2 嚴格結構與引用驗證、root 優先序及舊根目錄拒絕；承接五欄位、原子保存、備份復原與刪除 token，不遷移 v1。
- [X] T010 在 `air_defense/progression.py` 建立十二種封閉請求、canonical 指紋、身分／輪次與業務拒絕處理骨架；尚未實作的業務處理不得回 applied。
- [X] T011 在 `air_defense/save_data.py` 整合完整候選交易與原子寫入；在 `air_defense/state.py` 建立 PendingSave、save_error 阻擋及原候選重試／來源頁恢復，重試不得再次 transact。
- [X] T012 新增 `air_defense/loadout.py` 解析不可變 EffectiveWeaponStats／EffectivePlayerStats／BattleLoadout，依基本值→個別升級→配件計算；先提供無裝甲基準與完整武器能力。
- [X] T013 新增 `air_defense/deployment.py` 的 WorldDefinition、純射線／可見性與地圖幾何查詢，完成純 validate_placement／validate_deployment 的有限座標、所有權、容量、地圖內縮、塔距、障礙／出生區／通道邊界，供 US1 確認及歷史配置修正；`air_defense/scene.py` 由同一份邊界／障礙物／出生區／通道建立世界，保留現有碰撞回歸。
- [X] T014 更新 `tests/test_save_data.py`、`tests/test_contracts.py`、`tests/test_save_recovery.py` 與 `tests/test_slot_isolation.py` 的 v1 衝突期待，執行本階段測試並將結果記於 `artifacts/002-gameplay-expansion/foundation.md`。

**關卡**：基礎測試通過後才開始故事；不要求尚未實作的故事交易假裝可用。

## 階段 3：US1 新檔準備與第一場戰鬥（P1／MVP）

**目標**：免費三武器即可經三步準備、安全確認並開始 1-1。

**獨立驗收**：新檔 2 分鐘內經鳥瞰預覽開始；缺空地、重複或未擁有武器被拒絕；空槽合法；取消不扣款；保存失敗不開戰。免費裝備通過 1-1 後只發一次獎勵並回主選單等待手動開始下一關；失敗原關重試。

### 先建立驗證

- [X] T015 [P] [US1] 在 `tests/test_preparation.py` 覆蓋三步返回／取消、零裝甲零塔、五槽重排、草稿隔離與非法歷史部署撤回庫存。
- [X] T016 [P] [US1] 在 `tests/test_preparation_flow.py` 覆蓋保存前無 BattleState、確認失敗重試回確認頁、重新開始才建新 AttemptId、首個非空槽及完整免費首局；驗鳥瞰進出還原鏡頭、首局 reward／failure 身分及輪次、重複 settle、結算寫入失敗重試與下一關手動開始。

### 實作與整合

- [X] T017 [US1] 新增 `air_defense/preparation.py` 管理草稿身分／revision／輪次、步驟與驗證訊息；在 `air_defense/loadout.py` 驗五槽所有權、不重複及至少一空一地。
- [X] T018 [US1] 在 `air_defense/progression.py` 實作 confirm_loadout、reward、failure 三種 v2 業務交易；確認前重新驗證槽位、裝甲、部署容量與幾何。承接既有獎勵公式、失敗零獎勵與資格規則，各請求帶 profile_id／rebirth_count；confirm_loadout 帶 loadout，reward／failure 帶 a／b／A，嚴守各自封閉契約，經共用去重及原子保存；不沿用 v1 請求形狀。
- [X] T019 [US1] 在 `air_defense/state.py` 接入準備路由、保存後建立當局、草稿取消與原關失敗重試；將當局專屬 AttemptId 結算接到 T018，成功推進 cursor 並經結果頁回主選單等待手動開始，失敗不推進，結算寫入失敗保留完整候選且重試不重發。當局由配置快照建立，準備期間不推進敵人。
- [X] T020 [US1] 新增 `air_defense/weapons.py` 的逐武器 runtime 與 `air_defense/entities.py` 的有序命令／事件型別，先完成免費手槍、狙擊槍的射空耗彈、上膛與換彈，以及 W01 鎖定發射。
- [X] T021 [US1] 在 `air_defense/state.py` 與 `air_defense/combat.py` 將免費首局改由 weapon_id／配置能力驅動；移除首局固定槽位及預設六塔假設，維持空地威脅清完才成功。
- [X] T022 [US1] 在 `air_defense/ui.py` 與 `air_defense/main.py` 實作裝甲→五槽→部署→確認頁及基本有序 fire_down/up、reload、select_slot 適配；r=0 顯示零容量與預覽，禁止出戰時修改裝備。
- [X] T023 [US1] 在 `air_defense/scene.py` 與 `air_defense/audio.py` 將免費三武器模型、瞄準、HUD／聲音選擇改讀 weapon_id；在 `air_defense/scene.py` 建立基本 DeploymentView 正交鳥瞰與 r=0 地圖預覽，進出保存／還原鏡頭、fov、parent 及滑鼠捕捉，接入 T022 路由。鳥瞰互動延至 US5；本階段可沿用既有造型，數值不得由呈現回寫。
- [X] T024 [US1] 更新 `tests/test_story1_vertical.py`、`tests/test_app_state.py` 的首局流程，執行 US1 獨立驗收並保存操作步驟／耗時與結果至 `artifacts/002-gameplay-expansion/us1.md`。

**關卡**：US1 的上述獨立驗收與受影響回歸均通過，才能標記本故事完成。

## 階段 4：US2 二十武器購買、自訂與成長（P1）

**目標**：商品可購買、逐把升級與自訂，商店結果與當局能力一致。

**獨立驗收**：20 武器分類正確；升級 W17 不改 W18；相容配件同時套用收益與代價；重選已購外觀不扣款；商店不能直接換出戰裝備。

### 先建立驗證

- [X] T025 [P] [US2] 在 `tests/test_weapon_shop.py` 覆蓋價格、餘額、重購、未擁有／不相容項目、升級 cap 與 W17/W18 隔離。
- [X] T026 [P] [US2] 在 `tests/test_weapon_customization.py` 覆蓋七配件三槽、逐把外觀所有權、免費選用、有效值計算順序與預覽／當局一致。

### 實作與整合

- [X] T027 [US2] 在 `air_defense/progression.py` 完成 purchase_weapon、upgrade_player、upgrade_weapon；依目錄定價，升級只修改指定實體與適用項。
- [X] T028 [US2] 在 `air_defense/progression.py` 完成 purchase_attachment、purchase_cosmetic、customize_weapon，購買不自動選用，未知欄位／未擁有選用不可套用。
- [X] T029 [US2] 在 `air_defense/loadout.py` 完成所有武器升級及配件邊界能力解析，包括兩狙擊各自射程、AA 鎖定／白框／輔助與火箭裝填取捨。
- [X] T030 [US2] 在 `air_defense/ui.py` 建立自身血量／裝甲／砲塔／武器四商店、3×2 卡片分頁及武器分類；顯示現值、下級、價格、所有權與明確不可購原因，裝甲／砲塔處理接續 US4／US5。
- [X] T031 [US2] 在 `air_defense/ui.py` 加入武器自訂頁與配件／配色／圖樣頁籤，顯示解析後能力與代價；商品選用不寫出戰槽。
- [X] T032 [US2] 在 `air_defense/main.py` 與 `air_defense/state.py` 將商店操作接入穩定 operation_id、完整交易與保存錯誤返回原頁；移除舊商店數字鍵購買路由。
- [X] T033 [US2] 執行購買、自訂、配置後進戰鬥的 US2 情境及受影響 `tests/test_weapon_validation.py`，將商品／能力對照證據記於 `artifacts/002-gameplay-expansion/us2.md`。

**關卡**：US2 的上述獨立驗收與受影響回歸均通過，才能標記本故事完成。

## 階段 5：US3 射擊模式、彈藥與實體投射物（P1）

**目標**：二十武器具備完整射擊時序、可見彈道及公平碰撞。

**獨立驗收**：六模式及 30/60/144 Hz 結果符合契約；短點擊不遺失；兩火箭每關各 3／5 發、首次碰撞才傷害；切槍／暫停不補彈或重複傷害。

### 先建立驗證

- [X] T034 [P] [US3] 在 `tests/test_weapon_timing.py` 覆蓋六模式、0.06 秒射速餘量、三連發不足三發、R／空匣換彈、逐把彈匣與切槍冷卻。
- [X] T035 [P] [US3] 在 `tests/test_input_commands.py` 覆蓋同微步 down/up、先射後切／先切後射、重複 down、暫停優先與失焦放開保護。
- [X] T036 [P] [US3] 在 `tests/test_rocket_collision.py` 覆蓋發射近牆、薄牆掃掠、首次命中、同距世界優先、表面爆炸可見性、半徑／射程端點、到期與傷害對象。
- [X] T037 [P] [US3] 在 `tests/test_hitscan_v2.py` 覆蓋射空消耗、狙擊超過 180、八彈丸同敵、每顆只傷最近目標及遮擋。

### 實作與整合

- [X] T038 [US3] 在 `air_defense/weapons.py` 完成六模式時刻排程、burst 間隔／取消、bolt、手動／自動換彈及每武器火箭 quota，使用有效時間而非逐發捨入。
- [X] T039 [US3] 在 `air_defense/state.py` 完成 120 Hz／最多八步的命令保留與依序消費，依契約七步順序整合移動、敵人、射擊、彈體與勝負；一次 down 不得再被 auto 重發。
- [X] T040 [US3] 在 `air_defense/combat.py` 實作有效射程最近碰撞與固定中心加七環霰彈，以 shot_id／pellet_index 區分傷害來源，無目標仍可射擊。
- [X] T041 [US3] 新增 `air_defense/projectiles.py` 實作直線火箭、剩餘射程／壽命截段及世界／地面／敵人掃掠，對同距接觸採世界優先與穩定序。
- [X] T042 [US3] 在 `air_defense/projectiles.py` 與 `air_defense/combat.py` 完成接觸點爆炸、normal 偏移可見性與每敵一次傷害；不傷玩家、城市、塔或飛機，到期無爆炸。
- [X] T043 [US3] 在 `air_defense/combat.py` 與 `air_defense/projectiles.py` 完成 W01/W02 固定目標導彈、發射能力快照、多目標整批建立及失敗不扣半份資源。
- [X] T044 [US3] 在 `air_defense/main.py` 接入完整原生輸入佇列、全域 fire_up、R、瞄準及失焦／恢復；UI 焦點不得將商店操作送入戰鬥。
- [X] T045 [US3] 在 `air_defense/state.py` 輸出含 runtime、瞄準倍率、彈體及 diagnostics 的唯讀快照與唯一事件，結束清掉點放／輸入／鎖定並忽略舊 attempt。
- [X] T046 [US3] 在 `air_defense/scene.py` 實作每次有效射擊可見的曳光／槍口／命中與實際飛行彈體、換彈／上膛動畫，核心彈道不因額外粒子池已滿消失。
- [X] T047 [US3] 在 `air_defense/audio.py` 與 `air_defense/ui.py` 接入 weapon_id 音效、16 聲部、彈匣／配額／模式／換彈進度及準心；設定與瞄準不回寫能力。
- [X] T048 [US3] 更新 `tests/test_weapon_integration.py`、`tests/test_pause_focus.py`、`tests/test_multi_lock.py` 與 `tests/test_rpg_turrets.py` 的衝突舊期待，執行全武器矩陣並將 V03/V04 結果記於 `artifacts/002-gameplay-expansion/us3.md`。

**關卡**：US3 的上述獨立驗收與受影響回歸均通過，才能標記本故事完成。

## 階段 6：US4 六種裝甲與玩家能力（P1）

**目標**：可購買六種固定裝甲，準備時選零或一件並明確感受差異。

**獨立驗收**：六套生命／移速／減傷／回血效果符合表；換裝不疊加，回血預算與正傷害下限正確，城市不受玩家裝甲影響。

### 先建立驗證

- [X] T049 [P] [US4] 在 `tests/test_armor_loadout.py` 覆蓋六裝甲所有權、零／一件配置、重購、固定不可升級與換裝不疊加。
- [X] T050 [P] [US4] 在 `tests/test_armor_combat.py` 覆蓋生命／速度／跳躍、傷害下限、回血等待／速率／20% 預算及城市傷害隔離。

### 實作與整合

- [X] T051 [US4] 在 `air_defense/progression.py` 完成 purchase_armor；在 `air_defense/loadout.py` 解析六裝甲與自身血量升級的有效玩家能力。
- [X] T052 [US4] 在 `air_defense/entities.py` 與 `air_defense/state.py` 套用有效最大生命、移動、減傷及回血時序／預算，不新增爆炸抗性或玩家爆炸傷害。
- [X] T053 [US4] 在 `air_defense/ui.py` 與 `air_defense/main.py` 完成六裝甲商店比較、購買、準備穿戴／不穿與能力預覽，沿用完整交易錯誤路由。
- [X] T054 [US4] 執行六裝甲戰鬥情境並更新 `tests/test_player_health.py`，保存各能力實測與城市對照至 `artifacts/002-gameplay-expansion/us4.md`。

**關卡**：US4 的上述獨立驗收與受影響回歸均通過，才能標記本故事完成。

## 階段 7：US5 逐台砲塔購買與鳥瞰部署（P1）

**目標**：依重生容量自由部署已購個別砲塔，三種塔按公平規則戰鬥。

**獨立驗收**：r=0/1/2/4/6 容量為 0/2/4/8/12；同型各台身分不同；放置與預覽相符；T03 可見一秒，對地塔不能打穿 Boss 精確半血。

### 先建立驗證

- [X] T055 [P] [US5] 在 `tests/test_turret_inventory.py` 覆蓋 r=0 禁購、逐台 ID／操作重播、庫存可超容量、同台不得重複部署及跨關保留。
- [X] T056 [P] [US5] 在 `tests/test_deployment.py` 覆蓋地圖內縮、障礙相切、塔距 3／2.99、出生區、通道、非法歷史位置及有限座標。
- [X] T057 [P] [US5] 在 `tests/test_turret_targeting.py` 覆蓋水平端點、遮擋／穩定選敵、T03 重鎖／兩秒間隔及奇數最大生命 Boss 混合塔半血。

### 實作與整合

- [X] T058 [US5] 在 `air_defense/progression.py` 完成 purchase_turret，使用 turret-操作ID 建立每台庫存，只限制部署量 2r，不新增庫存或六塔上限。
- [X] T059 [US5] 在 `air_defense/deployment.py` 承接 T013 的純放置驗證，補齊移動排除自身／取消還原與 72 角×16 徑向射程預覽，共用世界可見性並標示地面近似／防空高度限制。
- [X] T060 [US5] 在 `air_defense/preparation.py` 與 `air_defense/loadout.py` 接入部署草稿及出戰複驗，失效位置撤回庫存且保留原因，依 instance_id 穩定建立當局塔。
- [X] T061 [US5] 在 `air_defense/scene.py` 擴充 T023 的基本鳥瞰，實作 Lens.extrude 地面投影、WASD／中鍵平移、滾輪與按鈕縮放、置中及選取／移動／移除互動，顯示合法／非法位置與射程預覽。
- [X] T062 [US5] 在 `air_defense/ui.py` 與 `air_defense/main.py` 完成三塔卡片／逐台庫存、放置／移動／移除、容量提示及側欄點擊攔截，r=0 僅預覽。
- [X] T063 [US5] 在 `air_defense/entities.py` 與 `air_defense/state.py` 建立 TurretRuntime、三類選敵／時刻與 T03 持續可見計時，從確認配置建立任意合法數量。
- [X] T064 [US5] 在 `air_defense/combat.py` 與 `air_defense/projectiles.py` 接入塔傷害來源、防空導彈與地面 Boss max_hp/2 精確下限，不使用固定原始 Boss 生命。
- [X] T065 [US5] 執行五種容量、鳥瞰真實點擊與混合塔戰鬥，將 V06 幾何邊界／預覽／選敵證據記於 `artifacts/002-gameplay-expansion/us5.md`。

**關卡**：US5 的上述獨立驗收與受影響回歸均通過，才能標記本故事完成。

## 階段 8：US6 戰役成長與重生全清（P1）

**目標**：自動依 a,b 成長、免費武器可完成首輪，重生清除全部付費成果。

**獨立驗收**：七關獎勵合計 1560；失敗原關重試、重開 1-1；重生門檻 1000(r+1)、全清並重發三武器，歷史／設定保留，舊輪請求不污染新輪。

### 先建立驗證

- [X] T066 [P] [US6] 在 `tests/test_difficulty_v2.py` 覆蓋四成長公式、精確向上取整、上限、a=b=1 基準、空降快照及具名飛行參數。
- [X] T067 [P] [US6] 在 `tests/test_rebirth_v2.py` 覆蓋所有付費類別／自身升級全清、重發免費三把、歷史／設定保留與新舊輪操作競爭。
- [X] T068 [P] [US6] 在 `tests/test_campaign_v2.py` 覆蓋七獎勵、原關重試、重啟／重生 cursor、同規模重打及重複／過期 AttemptId。

### 實作與整合

- [X] T069 [US6] 在 `air_defense/progression.py` 實作 difficulty_for 與 rebirth 交易／門檻；沿用 T018 的 reward／failure 並驗完整戰役的獎勵與資格，不另建第二套結算。重生完整候選全清且保留歷史。
- [X] T070 [US6] 在 `air_defense/entities.py` 與 `air_defense/state.py` 改用具名飛行時間／角速度／偏航及敵人有效 max_hp，出生／空降共用 DifficultySnapshot，速度與轉向實際套用。
- [X] T071 [US6] 在 `air_defense/state.py` 沿用 T019 的當局結算及原關重試，補齊最終成功同規模重打、重生回 1-1 與資格重設，保存失敗不得先繼續新輪。
- [X] T072 [US6] 在 `air_defense/ui.py` 與 `air_defense/main.py` 顯示 a,b 自動強度、獎勵／資格與重生全清確認，不新增玩家難度選項。
- [X] T073 [US6] 新增 `tools/expansion_probe.py` 的 economy 情境，用公開移動／瞄準／射擊控制免費三武器完成 A=2 七關，記錄每關投入／獎勵，禁止直接改血、跳勝利或加錢當通關證據。
- [X] T074 [US6] 更新 `tests/test_economy.py`、`tests/test_campaign_progression.py`、`tests/test_aircraft_rules.py`、`tests/test_restart_persistence.py` 的契約期待，保留 A=19 編隊及獨立 FAST 驗證，執行免費七關通關、合法首次重生，再以重發三武器／無裝甲／無塔實際完成新輪 1-1，記錄敵人基準強度、結算與剩餘資產至 `artifacts/002-gameplay-expansion/us6.md`。

**關卡**：US6 的上述獨立驗收與受影響回歸均通過，才能標記本故事完成。

## 階段 9：US7 全面糖果風與安全續玩（P2）

**目標**：全部畫面使用原創一致糖果風，五欄位完整續玩並保護舊版資料。

**獨立驗收**：20 模型各兩項輪廓差異、六裝甲及全場景一致；兩解析度無遮擋；五欄位完整往返，十二交易故障重試不重複，舊檔 bytes／mtime 不變。

### 先建立驗證

- [X] T075 [P] [US7] 在 `tests/test_save_v2_matrix.py` 建立十二交易逐一 replace 失敗／重試、程序中斷、五欄位所有商品往返、舊根 bytes／mtime 與設定保留矩陣。
- [X] T076 [P] [US7] 在 `tests/test_visual_catalog.py` 驗證二十武器各兩輪廓部件、六裝甲／三塔配方與共用預覽識別，檢查造型定義不攜帶戰鬥傷害邏輯。

### 實作與整合

- [X] T077 [US7] 新增 `air_defense/visual_catalog.py`，依呈現契約建立二十武器原創輪廓、六裝甲、三塔及糖果色／圓潤世界配方。
- [X] T078 [US7] 新增 `air_defense/models.py` 的圓角盒／膠囊等共用模型工廠與離線圖樣，生成所需 `assets/textures/` 資產；商店、自訂、第一人稱與世界共用同商品造型。
- [X] T079 [US7] 在 `air_defense/scene.py` 套用糖果城市、地面／掩體、四飛機、豆形敵兵／Boss、玩家武器／裝甲與三塔，維持純規則碰撞包絡不隨美術改變。
- [X] T080 [US7] 在 `air_defense/ui.py` 完成選檔、主選單、四商店、自訂、準備／確認、HUD、暫停、結果及錯誤頁整體糖果風，校正中文、焦點與兩解析度排版。
- [X] T081 [US7] 在 `air_defense/models.py`、`air_defense/scene.py` 與 `air_defense/audio.py` 完成預覽釋放、24/48/80 額外粒子池、必備彈道保留、缺資產／無音訊與低畫質回退。
- [X] T082 [US7] 完成 `air_defense/save_data.py` 與 `air_defense/state.py` 的十二交易故障矩陣缺口，確保備份失敗不覆蓋、未知版本保留、刪除 token 過期失效、正常重試與強制終止結果可區分。
- [X] T083 [US7] 更新 `tools/engine_probe.py` 的 expansion／size／output 介面及 `tools/review_engine_probe.py` 的舊固定槽位假設，建立所有畫面兩解析度擷取。
- [X] T084 [US7] 擴充 `tools/expansion_probe.py` 的 catalog 情境，輸出 20 武器兩項輪廓差異、六裝甲、三塔與客製預覽／戰鬥一致性證據。
- [X] T085 [US7] 在 `assets/LICENSES.md` 記錄新增原創模型、圖樣及音效來源／授權，保留既有字型授權且確保全部必要素材隨包。
- [X] T086 [US7] 執行 V08/V09 保存與畫面矩陣，逐張檢查 1280×720／1920×1080，將缺陷修復後證據及真實鍵鼠完整流程記於 `artifacts/002-gameplay-expansion/us7.md`。

**關卡**：US7 的上述獨立驗收與受影響回歸均通過，才能標記本故事完成。

## 階段 10：整合驗證與交付收尾

**目標**：完成跨故事實測與需求追蹤，再依憲章執行 GitHub 交付；依下列任務完成驗收及交付。

- [X] T087 擴充 `tools/expansion_probe.py` 的 lifecycle 情境及 `tests/test_lifecycle_metrics.py`，完成十輪準備／戰鬥／暫停／結果／返回，記錄 Entity、task、handler、彈體、UI 及另列快取基準。
- [X] T088 更新 `tools/performance_probe.py` 與 `tests/test_performance_scenarios.py`，支援 aircraft／warmup／duration／output，A8 情境實際包含 r=6 十二塔、全自動與兩種火箭，輸出原始幀時間與逐秒物件數。
- [X] T089 執行 `specs/002-gameplay-expansion/quickstart.md` 的 A4／A8 各暖機 10 秒量測 60 秒及十輪生命週期；不達 A4 平均 55／P1 45 FPS 或連續兩幀各超過 250 ms 時修復並重驗，保存至 `artifacts/002-gameplay-expansion/performance.md`。
- [X] T090 驗證並修正 `start_game.cmd`、`tools/launch.cmd`、`tools/bootstrap.py` 的中文空白路徑、離線後續啟動、無音訊／缺可選資產／低畫質；執行 `tests/test_launcher_contract.py`，保存實測至 `artifacts/002-gameplay-expansion/launcher.md`。
- [X] T091 執行 `run_tests.cmd`、compileall 與受影響工具完整驗證，確認純規則不依賴引擎及所有新舊契約回歸，保存命令／退出碼至 `artifacts/002-gameplay-expansion/verification.md`；只因新修改或失敗重跑相關檢查。
- [X] T092 更新 `README.md`、`SPEC-KIT.md`、`docs/DECISIONS.md` 及 `specs/002-gameplay-expansion/quickstart.md` 為實際完成的 v2 操作／保存／工具說明，檢查繁體中文與相對連結，歷史 001 證據不改寫。
- [X] T093 依 speckit-converge 檢查實作與 spec／plan／`specs/002-gameplay-expansion/tasks.md`，將真實缺口追加任務並完成必要重驗，在 `artifacts/002-gameplay-expansion/acceptance.md` 逐項連結 34 FR／12 SC 證據，未驗項不得標通過。
- [ ] T094 確認驗收完成後在 `artifacts/002-gameplay-expansion/pr-body.md` 撰寫問題、改變、規格與實際驗證；核對分支／main 目標及 gh 認證，以 gh 原生命令或 gh api 發佈工作分支並建立 PR，正文使用 --body-file，記錄 PR URL。
- [ ] T095 以 gh 結構化結果核對必要檢查／審查後完成 PR 合併，將目標分支、合併結果與變更納入證據記於 `artifacts/002-gameplay-expansion/delivery.md`；不得直接推送 main 或將 PR 關閉視為合併。
- [ ] T096 確認無未保存／未納入提交及其他工作樹佔用後，透過 gh 同步目標遠端內容並切回本機 main，使用本機 git 清除工作分支及失效追蹤參照、gh 清除遠端分支；核對兩端均不存在並補記 `artifacts/002-gameplay-expansion/delivery.md`，不能確認時保留並記錄原因。

**關卡**：所有需求具真實證據且交付狀態可查；失敗或未驗證項保持未勾選。

## 依賴與執行順序

```mermaid
flowchart LR
  S["階段 1 環境"] --> F["階段 2 共用基礎"]
  F --> U1["US1 免費首局"]
  U1 --> U2["US2 購買自訂"]
  U2 --> U3["US3 完整戰鬥"]
  U3 --> U4["US4 裝甲"]
  U4 --> U5["US5 砲塔"]
  U5 --> U6["US6 戰役重生"]
  U6 --> U7["US7 美術續玩"]
  U7 --> P["整合驗證與交付"]
```

此圖是本次單線整合／完成順序，承接 plan 的批次並按使用者故事組織。主要技術依賴如下：

| 故事 | 必要前置與界線 |
| --- | --- |
| US1 | 共用基礎；自己完成免費三武器基本射擊、準備、基本鳥瞰及 reward／failure 結算，無須等 US3 全模式、US5 付費部署或 US6 重生。r=0 無裝甲／零塔也能完成首局。 |
| US2 | 共用交易與 US1 路由／配置；本故事驗商品所有權、自訂與有效值，全部射擊模式的戰鬥矩陣由 US3 驗。 |
| US3 | US1 的 runtime／輸入與 US2 的完整能力解析；不依賴裝甲、砲塔或新美術。 |
| US4 | US1 配置、US2 商店／交易及 US3 穩定傷害步序；以隔離裝甲資料重跑能力情境。 |
| US5 | US1 準備、US2 商店、US3 投射物／傷害；US4 先整合以避免共用 UI／state 衝突，零裝甲仍可驗塔。 |
| US6 | US2／US4／US5 商品交易完整後驗「全部付費成果」清除；敵人成長與免費通關使用 US3 戰鬥核心。 |
| US7 | 前六故事提供所有畫面／實體及十二交易；模型配方可提早設計，但本故事完成須完整功能與保存矩陣。 |

每階段的測試檔撰寫可平行，實作任務依 ID 順序；測試使用階段 1 的共用 fixture，新增案例不得同時修改 fixture。新需求造成測試 fixture 必須變更時，先單獨完成該變更再啟動平行測試工作。

## 各故事平行範例

下列是可分工的任務組合，不代表本次已啟動其他代理。每組只同時撰寫不同測試檔；完成後共同檢查行為失敗再進入實作。

| 故事 | 可同時處理的任務 | 啟動時機 |
| --- | --- | --- |
| US1 | `T015`、`T016` | 前一階段關卡完成後 |
| US2 | `T025`、`T026` | 前一階段關卡完成後 |
| US3 | `T034`、`T035`、`T036`、`T037` | 前一階段關卡完成後 |
| US4 | `T049`、`T050` | 前一階段關卡完成後 |
| US5 | `T055`、`T056`、`T057` | 前一階段關卡完成後 |
| US6 | `T066`、`T067`、`T068` | 前一階段關卡完成後 |
| US7 | `T075`、`T076` | 前一階段關卡完成後 |

共用基礎另有 T004、T005、T006 可同時撰寫。跨故事的 main.py／state.py／ui.py 修改保持依序，沒有標成平行工作。

## 需求覆蓋與驗證入口

| 驗收組 | 規格需求 | 主要任務 | 證據入口 |
| --- | --- | --- | --- |
| V01 | FR-001、FR-002、FR-003、FR-004；SC-001 | T001–T024 | us1.md、foundation.md |
| V02 | FR-005、FR-006、FR-007、FR-008、FR-009；SC-002、SC-003 | T004、T007、T012、T025–T033、T049–T065、T076–T086 | us2.md、us4.md、us5.md、us7.md、catalog/ |
| V03 | FR-010、FR-011、FR-012、FR-015、FR-016；SC-004 | T034–T048 | us3.md |
| V04 | FR-013、FR-014；SC-005 | T036、T040–T043、T048 | us3.md |
| V05 | FR-017、FR-018；SC-006 | T049–T054 | us4.md |
| V06 | FR-019、FR-020、FR-021、FR-022；SC-007 | T055–T065 | us5.md |
| V07 | FR-023、FR-024、FR-025、FR-026、FR-027；SC-008 | T018–T019、T066–T074 | us1.md、us6.md、economy/ |
| V08 | FR-002、FR-028、FR-029、FR-030；SC-009 | T005–T011、T014、T016、T018–T019、T075、T082、T086 | foundation.md、us7.md |
| V09 | FR-031、FR-032、FR-033；SC-010 | T076–T081、T083–T086 | us7.md、catalog/、1280x720/、1920x1080/ |
| V10 | FR-034、FR-015、FR-016、FR-020；SC-011、SC-012 | T087–T091 | performance.md、launcher.md、lifecycle/、verification.md |
| 交付治理 | 憲章 I–VIII | T092–T096 | acceptance.md、pr-body.md、delivery.md |

本表證據入口皆位於 `artifacts/002-gameplay-expansion/`；完成狀態以任務勾選與實際報告為準。完整要求及測量步驟見 quickstart.md 與四份契約。

## 十二交易歸屬

| 實作任務 | 交易 |
| --- | --- |
| T018 | confirm_loadout、reward、failure |
| T027 | purchase_weapon、upgrade_player、upgrade_weapon |
| T028 | purchase_attachment、purchase_cosmetic、customize_weapon |
| T051 | purchase_armor |
| T058 | purchase_turret |
| T069 | rebirth（延伸驗證既有 reward／failure） |

T010–T011 提供共用驗證／保存框架；T075、T082、T086 在十二處理器完成後執行逐類故障／重試矩陣。不可將框架測試當成全部交易效果已驗證。

## 增量交付策略

1. **MVP**：完成 T001–T024（24 項），新檔三免費武器經基本鳥瞰、準備保存後可完成首局、結算保存並手動開始下一關。此階段無需全部新造型，但不得省略保存與配置安全。
2. 完成 US2／US3，交付完整武器庫、客製與射擊；再加 US4／US5 的裝甲與部署，每個增量重跑前面受影響測試。
3. 完成 US6 的經濟／成長／全清與 US7 的全面造型／續玩，再執行整合測量與需求收斂。
4. 只有實際完成的任務才勾選。文件生成不提交／發佈／合併；後續交付依授權與憲章，以 gh 原生命令／gh api 處理全部 GitHub 遠端操作，本機 git 僅用於本機工作。
5. PR 檢查、合併或分支清理未確認時保留工作並記錄，不能跳過關卡宣稱完成。

## 任務統計

| 範圍 | 數量 |
| --- | --- |
| 環境 | 3 |
| 共用基礎 | 11 |
| US1 | 10 |
| US2 | 9 |
| US3 | 15 |
| US4 | 6 |
| US5 | 11 |
| US6 | 9 |
| US7 | 12 |
| 整合與交付 | 10 |
| 原始任務小計 | 96 |
| 第 11 階段收斂追加 | 2 |
| 合計 | 98 |

共 21 項標示 `[P]`；全部為獨立檔案的測試撰寫工作。任務 ID 連續、故事標籤與階段一致，所有任務附具體檔案路徑。


## Phase 11: Convergence

本階段為收斂檢查追加；既有任務順序與編號維持不變。檢查 34 項 FR、12 項 SC、35 個故事驗收情境、11 個邊界情況、9 組技術決策及 8 項憲章原則，發現兩項 partial：HIGH 1 項、LOW 1 項；missing／contradicts／unrequested 均為 0。原生失焦等證據限制依呈現契約明列，未冒充已驗證。

- [ ] T097 完成既有 T094–T096 的 GitHub PR、必要檢查、合併確認及安全分支清理，在 `artifacts/002-gameplay-expansion/delivery.md` 記錄實際結果與來源；依 T094–T096、憲章 VII／VIII（partial，HIGH，F1）。
- [X] T098 更新 `specs/002-gameplay-expansion/spec.md` 與 `specs/002-gameplay-expansion/plan.md` 的實作／驗收階段狀態並連結實際證據，保留設計階段的歷史測試基準，核對文件連結與任務統計；依 T092／T093、憲章 III（partial，LOW，F2）。
