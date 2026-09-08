# 任務清單：多人 PvP 空中躲避與地面防空

**輸入**：[規格](spec.md)、[計畫](plan.md)、[研究](research.md)、[資料模型](data-model.md)、[多人契約](contracts/multiplayer.md)、[畫面契約](contracts/ui.md)、[驗證指南](quickstart.md)。

**狀態**：任務已產生，已開始依序實作；僅已執行並驗證項目勾選。完整功能與正式發布仍須通過最後驗收。

**格式**：`- [ ] T編號 [P] [US編號] 說明與路徑`。[P] 只表示該階段可在不同檔案獨立進行，並非自行授權啟動代理；未標示者依列出順序執行。路徑相對於專案根目錄。

**測試規則**：spec 明確要求驗證，因此先寫對應失敗測試、確認能捕捉缺陷，再實作至通過；既有基線通過不等於新增功能完成。不修改已套用遷移或玩家存檔。

## 第一階段：準備

建立可追溯基線，不建立新專案或升級依賴。

- [X] T001 核對 `specs/005-air-ground-pvp/plan.md`、既有依賴與分支基線，建立 `artifacts/005-air-ground-pvp/acceptance.md` 的待驗證區；保留既有未提交日誌。
- [X] T002 在 `web/package.json` 新增 PvP 純規則／控制／橋接／HTTP 測試命令，沿用現有鎖檔與執行環境，不改已存在測試。 明列 test:pvp:unit 包含 room／hud／controls／client 四支 Node 測試，另註冊 bridge／http 及依序遇錯即停的 test:pvp 彙總；Python 仍獨立執行。
- [X] T003 依 `specs/005-air-ground-pvp/quickstart.md` 執行既有單人／合作基線，將命令與結果寫入 `artifacts/005-air-ground-pvp/acceptance.md`；失敗先釐清再進入基礎開發。

## 第二階段：共用基礎

本階段完成才開始故事實作；時間、亂數與傳輸皆可替換，場景不判命中。

- [X] T004 [P] 在 `web/lib/pvp-types.ts` 定義模式、房間、角色、操作、快照、確認與終局型別，依 `specs/005-air-ground-pvp/contracts/multiplayer.md` 明列欄位。
- [X] T005 [P] 在 `tests/test_pvp_motion.py` 建立固定步、坐標、出生點、碰撞與基礎數值的測試夾具及初始失敗案例，不載入圖形引擎。
- [X] T006 在 `air_defense/pvp_motion.py` 建立固定戰區、出生點、幾何掃掠及純移動介面；在 `air_defense/pvp.py` 建立不讀存檔的角色與當局容器，依研究數值實作。
- [X] T007 更新 `web/db/schema.ts` 的模式、倒數、roster_revision、模擬租約、串流及結果欄位；以 drizzle-kit 於 `web/drizzle/` 生成下一份新增遷移與 metadata，核對舊遷移未變。 追加 departures 退出帳本與 input_received_at；保留目前成員 player_id 唯一索引，不用成員列保存退出歷史。
- [X] T008 在 `web/public/bridge.py` 建立 pvp_start／tick／predict／dispose 入口邊界，更新 `web/scripts/prepare.mjs` 與 `web/public/rules/manifest.json`，產生並核對兩個新增 Python 模組副本。
- [X] T009 在 `air_defense/pvp.py` 與 `web/lib/pvp-types.ts` 定義完整角色快照及事件確認，加入 runId／tick／phase／inputAck，事件環不得替代耐久與結果；本階段建立 suspended／取消水位與完整移動確認的基本契約及橋接案例，供 T024／T033 使用，T042 再加入過期與中止整合。
- [X] T010 在 `web/scripts/test-pvp-bridge.mjs` 建立 Pyodide 起迄與假時鐘夾具，驗證基礎雙陣營世界、無城市／AI／存檔副作用及清理；基礎測試通過後進入故事。

## 第三階段：US1 建立房間與隨機分隊（P1）

目標：可獨立展示大廳、準備與分隊。獨立驗收：2–8 個身分完成七組時限與三秒倒數，不要求完成戰鬥。

- [X] T011 [P] [US1] 先在 `web/scripts/test-pvp-room.mjs` 撰寫七種時限、容量分流、可注入亂數與分隊無偏向的失敗測試；合作倍率仍限四人。
- [X] T012 [P] [US1] 先在 `web/scripts/test-pvp-http.mjs` 建立獨立 Cookie、本機服務限制與清理，覆蓋 PvP 無 profile 準備、未準備拒絕、非房主開始拒絕、同時搶最後位及倒數取消。 加入 sync→resume→exchange 首次開局、同 instance 重試、過時串流拒絕及 serverNow／hostInputs 時刻的契約測試。
- [X] T013 [US1] 在 `web/lib/multiplayer-rules.ts` 新增 mode 容量與時限函式、Fisher–Yates 分隊及 PvP 準備驗證；不修改 partyMultiplier 的合作範圍。
- [X] T014 [US1] 在 `web/lib/multiplayer-server.ts` 實作 create／lobby／join／ready／start 的 PvP 分支與 roster_revision 比較更新，公布分隊、startsAt、serverNow、hostInstance 與初始化串流。 同時實作成員 sync 初始化查詢，回覆本人 currentStream／runId，避免首次開局的串流循環依賴。 本階段一併實作基本 resume 比較換代、instance 綁定、十秒資格檢查、exchange 輸入／hostInputs 與 countdown 推進／取消；基本 leave／逾時記帳及資格釋放也在此完成，不等待 T040；戰鬥快照可用 T010 的固定夾具。T040 補強戰鬥期間的競爭與終局整合。
- [X] T015 [US1] 在 `web/lib/multiplayer-client.ts` 接入模式、runId 與 countdown 回覆，倒數採戰鬥輪詢頻率，清除換局快照／輸入／命令，保留正確 fetch 接收者。 先 sync 初始化再 resume，等待室轉開局時不得發送舊輸入。 基本 instance 建立、sync→resume→exchange 與同串流重試本階段完成，重連與終局強化留 T041。
- [X] T016 [US1] 在 `web/components/multiplayer-lobby.tsx` 增加模式選擇、模式容量、預計雙隊／時限、四人分頁、PvP 準備與限制說明，隱藏合作裝備與倍率。
- [X] T017 [US1] 在 `web/lib/pvp-session.ts`、`web/lib/game.ts` 與 `web/app/page.tsx` 接入獨立 PvP 開局生命週期與三秒倒數，停止其他場景輸入，倒數期間不推進飛行／鎖定。
- [X] T018 [US1] 執行 US1 房間與 HTTP 情境，於 `artifacts/005-air-ground-pvp/acceptance.md` 記錄七種開局、八人上限與倒數退出的實際結果；未接戰鬥的 MVP 只作本機驗證。 須在未實作 US4 時單獨通過首次取得串流與倒數交換，避免跨階段循環依賴。

## 第四階段：US2 地面鎖定與擊落（P1）

目標：基礎防空炮對實際空中角色鎖定與命中。獨立驗收：使用可控制軌跡的空中測試角色驗證射擊，無需依賴 US3 的完整駕駛 UI。

- [X] T019 [P] [US2] 先在 `tests/test_pvp_battle.py` 撰寫基礎配裝隔離、固定框投影、三秒鎖定、0.75 秒失鎖、冷卻與兩次命中失敗測試。
- [X] T020 [P] [US2] 先在 `web/scripts/test-pvp-hud.mjs` 撰寫地面 view 到既有 HUD 的適配測試，核對中心取得框、唯一目標、失鎖與冷卻／可發射不混淆。
- [X] T021 [US2] 在 `air_defense/pvp_motion.py` 實作基本地面移動／跳躍／障礙滑動與視角限制，使用既定速度、高度、碰撞與戰區，禁止存檔成長介入。
- [X] T022 [US2] 在 `air_defense/pvp.py` 實作 W01 基礎鎖定、限角導彈與相對運動掃掠、傷害／擊落歸屬；穩定選同一目標，清除失效追蹤，不產生空降兵。
- [X] T023 [US2] 在 `web/public/bridge.py` 輸出地面 HUD 所需快照與每人獨立鎖定／冷卻，測試不同成長存檔進入後數值完全一致且橋接不呼叫交易。
- [X] T024 [US2] 在 `web/lib/pvp-session.ts` 接入地面操作、可靠命令去重、房主固定步與本人 view，保持共同世界只推進一次。
- [X] T025 [US2] 在 `web/lib/pvp-scene.ts` 呈現戰區、地面角色、W01 原型模型、真實飛機與朝向正確的導彈；整合 `web/lib/aiming-hud.ts`，不用第二套準心或命中計算。
- [X] T026 [US2] 執行地面規則／HUD／橋接情境，核對不同畫面更新率、失鎖重取、同時命中與無 AI 副作用，記錄至 `artifacts/005-air-ground-pvp/acceptance.md`。

## 第五階段：US3 駕駛、躲避與觀戰（P1）

目標：兩套飛行操作與雙視角可用。獨立驗收：以腳本威脅和假時鐘測飛行、越界與觀戰，再整合真人地面。

- [X] T027 [P] [US3] 先在 `tests/test_pvp_flight.py` 撰寫速度／轉向／翻滾上限、相反鍵、撞地／障礙掃掠、越界 4.99／5.00 秒、回界與不復活的失敗測試。
- [X] T028 [P] [US3] 先在 `web/scripts/test-pvp-controls.mjs` 撰寫雙輸入模式、靈敏度／反轉、視角切換、失焦清空、偏好壞值／保存失敗與快捷鍵不干擾表單的測試。 加入 PredictionFrame／tick 與控制包序號分離、權威基準回放、30／60／144 格、亂序確認與 120 步耗盡的失敗案例，供 T033 重跑。
- [X] T029 [US3] 在 `air_defense/pvp_motion.py` 實作持續前進、限幅偏航／俯仰／翻滾及可供預測回放的移動，依 research 固定翻滾與控制軸關係，不提供瞬移。
- [X] T030 [US3] 在 `air_defense/pvp.py` 實作飛機耐久、撞毀／越界／退出淘汰、真實威脅狀態及空中淘汰後禁止控制，保留完整結果與原因。
- [ ] T031 [US3] 在 `web/lib/pvp-controls.ts` 實作兩套操控、指標鎖定／重新取得、偏好鍵與錯誤提示，視角和觀戰操作保留本機，不發送假戰鬥命令。
- [X] T032 [US3] 在 `web/lib/pvp-scene.ts` 實作可辨識飛機、機尾／第一人稱鏡頭、機身滾轉、避障鏡頭與隊友觀戰，所有軌跡使用一致座標轉換。
- [X] T033 [US3] 在 `web/lib/pvp-session.ts` 串接 Python 共用移動預測與確認後回放、100 毫秒校正、遠端插值／200 毫秒外推上限，不預測命中、淘汰或勝負。 依多人契約實作 PredictionFrame、權威 tick 對齊、累積轉角與命令水位去重，以及緩衝耗盡後 suspended／取消確認／重建。
- [X] T034 [US3] 在 `web/components/pvp-panel.tsx` 與 `web/app/globals.css` 實作固定飛行設定／說明分頁、雙隊 HUD、耐久／速度／高度、威脅／越界、觀戰與共用靜音。
- [X] T035 [US3] 擴充 `web/scripts/test-pvp-bridge.mjs`，驗證八名角色的各自操作確認、地面與飛行分流、視角切換不改戰鬥、失鎖提示消退與觀戰不能控制隊友。
- [ ] T036 [US3] 依 `specs/005-air-ground-pvp/contracts/ui.md` 實際檢查雙操作、雙視角、三種視窗及固定設定頁，將輸入／畫面證據與未驗證項目記於 `artifacts/005-air-ground-pvp/acceptance.md`。

## 第六階段：US4 中斷、結算與既有玩法隔離（P2）

目標：有一致勝負與可理解中止，存檔零變更。獨立驗收：注入截止與連線事件，驗證兩人、八人正常及異常流程。

- [X] T037 [P] [US4] 先在 `tests/test_pvp_lifecycle.py` 撰寫截止時間前後命中、同時全退、中止優先、時間不可凍結、結果確定一次與資源清理測試。 包含仍有飛機但時間未到不得判 air 勝。
- [X] T038 [P] [US4] 先在 `web/scripts/test-pvp-client.mjs` 撰寫 inputStream 換代、低序號、舊局、漏包重送、命令確認、超量佇列、預測回放及 fetch 接收者測試。 擴充 T012 已驗證的首次加入戰局／新分頁初始化情境，覆蓋戰鬥重連時舊分頁不得搶回串流、取消確認後不回放舊 look_total／fire_down 的案例。
- [X] T039 [P] [US4] 擴充 `web/scripts/test-pvp-http.mjs` 的斷線與權限測試，涵蓋 9.99／10 秒、房主首包前後重載、非房主 snapshot／finish／abort 拒絕、PvP 收據零新增及再戰不推進關卡。 加入空中提前宣告勝利拒絕與 reason／elapsed／角色狀態不一致的案例。 加入同序號或 sync 不續輸入、0.99／1.00 秒停用，以及退出後立即加入／建立別房、舊局重送 leave 不刪新房資格、逾時與 resume 競爭的案例。
- [X] T040 [US4] 在 `web/lib/multiplayer-server.ts` 強化 T014 已有 resume／runId 驗證，強化 departures 原子記帳與成員資格釋放，實作 simulation_tick 租約與 abort／finish／again 分支，保留唯一結果且永不寫 PvP 合作收據。 串流初始化走 sync／resume；finish 必須核對 timeout 已達時限，不能僅因飛機存活結算。
- [X] T041 [US4] 在 `web/lib/multiplayer-client.ts` 強化 T015 已有 instance／resume 的十秒重連窗口與 PvP 結果分流；重試不能恢復舊串流，完成／中止不進入合作 acknowledge 或 reward 路徑。 被換代實例停止自動重連搶控制；suspended 仍送取消水位，確認後才恢復新輸入。
- [X] T042 [US4] 在 `web/lib/pvp-session.ts` 整合 T009 的取消確認，實作一秒過期輸入、固定步有限補算、落後逾一秒中止、房主重新整理／例外處理與退出清理；Esc／失焦不得停止全房模擬。 取消時前移已丟棄命令與視角確認水位，恢復需新 fire_down。 使用 hostInputs 的 inputReceivedAt、serverNow 與本機單調時鐘計算輸入年齡，永久退出只採伺服器 departures。
- [X] T043 [US4] 在 `air_defense/pvp.py` 實作截止最後一步與共同勝負順序、同時致命命中歸屬、永久退出及結果冪等，並透過 `web/public/bridge.py` 暴露完整終局。 空中時間勝利必須到時限，reason 與結果角色狀態一致。
- [X] T044 [US4] 在 `web/components/pvp-panel.tsx` 與 `web/components/multiplayer-lobby.tsx` 完成勝負／中止區別、每人狀態分頁、再戰重新準備、連線重試與返回大廳，保留結果直到使用者離開。
- [X] T045 [US4] 執行正常結束／中止／再戰／重連前後存檔與 mp_results 對比，在 `artifacts/005-air-ground-pvp/acceptance.md` 記錄零變更及原合作規則回歸結果。

## 第七階段：整體驗收與交付

本階段依賴四個故事完成；只以實際結果勾選，不將程式碼存在當成驗收。

- [X] T046 在 `web/scripts/test-pvp-http.mjs` 完成二人與八人端到端情境及 200／500 毫秒延遲、跳包與重送注入；測量共同結果對齊並拒絕正式網址作測試目標。
- [ ] T047 依 `specs/005-air-ground-pvp/quickstart.md` 檢查十次進出、指標鎖定、靜音／無音效、三視窗無垂直捲動與效能，將原始量測和畫面證據整理至 `artifacts/005-air-ground-pvp/acceptance.md`。
- [X] T048 執行全部受影響 Python／Node／Pyodide／HTTP 測試、既有合作與單人回歸、TypeScript 檢查及正式建置，在 `artifacts/005-air-ground-pvp/acceptance.md` 記錄命令與退出碼，修正失敗後重測。
- [ ] T049 逐項將 FR-001–FR-024、SC-001–SC-008 對應實測證據，更新 `specs/005-air-ground-pvp/tasks.md` 與 `artifacts/005-air-ground-pvp/acceptance.md`；未通過項目不可勾選或宣稱完成。
- [ ] T050 完成 `web/scripts/prepare.mjs` 副本一致性與 `web/pnpm-lock.yaml`／實際來源檢查，依 `AGENTS.md` 提交根目錄和 web Git 的相同網頁來源，排除憑證、存檔、測試身分、node_modules 與建置產物。
- [ ] T051 依 `AGENTS.md` 與 `specs/005-air-ground-pvp/plan.md` 推送功能分支、以 gh 建立 PR，附實際驗證與規格連結，核對檢查和合併結果、同步目標分支並清理已合併工作分支。
- [ ] T052 依 `web/.openai/hosting.json` 的既有 Sites 專案執行正式部署：成功建置的相同來源推送後讀完整 SHA，驗證封裝、保存版本、部署並輪詢至終態；只追加遷移，核對公開網域 HTTP 與版本。
- [ ] T053 將實際 GitHub PR／提交與部署結果記入 `artifacts/005-air-ground-pvp/acceptance.md`，在 T051 清理後從最新 main 另建符合 005 編號的文件分支，以獨立 PR 同步新增交付文件至 GitHub，核對合併並清理該分支；不得直接提交 main 或使用已刪除分支。文件 PR 不改已驗證的網頁來源；在既有瀏覽器分頁交付正式網址，停止本次開發服務並清除短期憑證。

## 依賴與執行順序

```text
準備 T001–T003 → 共用基礎 T004–T010 → US1 T011–T018
                                    → US2 T019–T026
                                    → US3 T027–T036
US1＋US2＋US3 → US4 T037–T045 → 整體交付 T046–T053
```

- US2／US3 規則測試可用固定名單獨立驗證；完整真人流程依賴 US1。建議實作順序為 US1、US2、US3、US4，因共同檔案多，不能整組故事同時修改。
- T004 型別與 T005 測試夾具可並行；T006 完成後才建立橋接與快照，T007 遷移在 HTTP 測試前完成。T009 與 T004 修改同檔，必須串行。
- 每個故事先執行其標記 [P] 的測試編寫；後續實作依序完成並重跑對應案例。T011、T012 不依賴彼此；T019、T020 亦同；T027、T028 亦同；T037、T038、T039 亦同。
- T022／T030／T043 共用 pvp.py，T021／T029 共用 pvp_motion.py，T014／T040 共用 multiplayer-server.ts，T017／T024／T033／T042 共用 pvp-session.ts，禁止重疊寫入。
- T049 的驗收關卡通過才可執行 T050–T053。GitHub 同步、合併與 Sites 發布為連續交付步驟；不將半成品公開成可遊玩的 PvP。

## 各故事的並行例子

| 故事 | 可並行的獨立工作 | 必須等待 |
| --- | --- | --- |
| US1 | T011 房間規則測試、T012 HTTP 測試 | 共用基礎與可用的本機資料結構 |
| US2 | T019 純規則測試、T020 HUD 適配測試 | 共用核心／型別；正式畫面整合等 US1 |
| US3 | T027 飛行規則測試、T028 控制偏好測試 | 共用核心；完整真人對戰等 US1／US2 |
| US4 | T037 生命週期、T038 傳輸、T039 HTTP 權限測試 | 前三個故事已具備整合入口 |

## 需求追溯與驗收重點

| 故事／階段 | 規格需求 | 成功標準 | 任務 |
| --- | --- | --- | --- |
| US1 | FR-001–FR-005、FR-022 | SC-001、SC-002 | T011–T018、T044 |
| US2 | FR-006–FR-009、FR-016 | SC-002、SC-006 | T019–T026、T043 |
| US3 | FR-010–FR-015、FR-021、FR-023–FR-024 | SC-003、SC-007、SC-008 | T027–T036 |
| US4 | FR-016–FR-020、FR-022 | SC-004–SC-006 | T037–T045 |
| 整體交付 | 全部需求與品質關卡 | SC-001–SC-008 | T046–T053 |

## 實作策略與完成條件

1. 先做 US1 房間／分隊 MVP，確認七組配置及權限；此為最小可驗證切片，不宣稱完整可玩 PvP。
2. 加入地面與飛行玩法後完成一局；接續驗證中止、再戰與資料隔離，再擴大到八人及延遲情境。
3. 依 quickstart 保留真實證據。若無法取得畫面、輸入或效能證據，明列未驗證，不能把任務全部勾選。
4. 每批適當測試通過後依專案 GitHub 流程同步；最終正式發布需所有需求關卡通過。本文件不授權修改正式玩家資料作測試。

總計 **53 項**：準備 3、基礎 7、US1 8、US2 8、US3 10、US4 9、整體交付 8；其中 **11 項**標記 [P]。已完成 45 項；T031、T036、T047 保留實際輸入／完整驗收，T049–T053 保留最終驗收與交付。GitHub 草稿同步可先保存已通過自動檢查的來源，不等於合併或正式發布。
