# 實作計畫：多人 PvP 空中躲避與地面防空

**分支**：`005-air-ground-pvp` | **日期**：2026-09-08 | **規格**：[spec.md](spec.md)

**輸入**：`specs/005-air-ground-pvp/spec.md`；本階段補齊 tasks 必要設計，不表示程式已完成。

## 摘要

新增獨立 PvP 規則與場景，沿用既有多人身分、HTTP 房間交換及 Sites。服務端負責房間資格、隨機分隊、倒數與中止條件，房主負責戰鬥真相。合作容量、成長、獎勵與存檔保持原契約。固定物理、連線與 UI 決策詳見 [研究](research.md)、[資料模型](data-model.md) 與 [介面契約](contracts/multiplayer.md)。

## 技術背景

- **語言與版本**：沿用 Python 3.12 相容純規則、TypeScript 5.9.3、Node >=22.13；不變更目前虛擬環境與鎖檔選定版本。
- **主要依賴**：既有 React 19.2.6、vinext 1.0.0-beta.5、Three.js 0.185.x、Pyodide 314.x、Drizzle 0.45.x；精確依賴以 `web/pnpm-lock.yaml` 為準，不因本功能升版。
- **保存**：既有 Sites D1 追加房間欄位；飛行偏好用獨立本機鍵；PvP 結果不寫合作收據或單人存檔。
- **測試**：Python unittest、Node test、Pyodide 橋接測試、獨立 Cookie 的本機 HTTP 整合及真實頁面／操作驗收；測試資料僅用本機服務。
- **目標**：桌面瀏覽器，鍵盤與滑鼠；2–8 人每房，不新增行動觸控或競技伺服器。
- **效能**：1/120 秒固定戰鬥步進；呈現目標每秒 60 格；200 毫秒往返條件下共同狀態一秒內對齊，500 毫秒延遲仍無重送副作用。這些是待驗證目標。
- **限制**：房主判定不能防止惡意房主；單次請求與快照保持既有大小限制；一秒輸入失效、十秒重連期限；模擬落後超過一秒中止，不丟棄經過時間繼續算勝負。

## 憲章檢查

研究前與設計後均核對憲章 1.4.0，結果如下：

| 原則 | 設計證據與關卡 |
| --- | --- |
| I 契約一致 | spec 既有契約對照限定 PvP 例外；數值完整，合作與歷史文件不改寫 |
| II 可決定規則 | Python 獨立 PvP 與共用移動，注入時間／亂數，不在場景計算傷害 |
| III 證據驗證 | quickstart 分層驗證；任務保留實機與網路測量，不宣稱設計即驗收 |
| IV 保存冪等 | runId、inputStream、序號、原子終局；禁止 PvP 收據；新遷移只追加 |
| V 品質回退 | 指標鎖定、保存及連線錯誤明示；固定視窗與靜音可用 |
| VI 繁體中文 | 所有 SDD 文件採繁體中文，程式識別與必要工具名保留原文 |
| VII 分支與 PR | 沿用 005 功能分支，文件與實作各以 PR 合併並核對／清理 |
| VIII GitHub | 使用 gh 查詢與 PR；Git 提交和傳輸依使用者較新 AGENTS 授權沿用既有設定 |

沒有未解決產品澄清或未選擇技術方案。原離線桌面技術限制由使用者已核准的 003／004／005 網頁多人範圍明確取代，桌面功能不改；不改憲章歷史文字。

## 專案結構

### 功能文件

`specs/005-air-ground-pvp/` 包含 spec、research、plan、data-model、contracts/multiplayer、contracts/ui、quickstart、tasks 及既有品質清單。

### 原始碼分工

| 路徑 | 責任 |
| --- | --- |
| air_defense/pvp.py | 獨立當局、鎖定、導彈、傷害、勝負與角色狀態 |
| air_defense/pvp_motion.py | 固定世界、飛行／地面移動、碰撞及預測共用運算 |
| web/public/bridge.py、web/scripts/prepare.mjs | PvP 專用橋接、純規則複製與模組清單；不複製存檔 |
| web/lib/pvp-types.ts、pvp-session.ts、pvp-controls.ts、pvp-scene.ts | 型別、生命週期／預測、輸入偏好、唯讀場景呈現 |
| web/lib/multiplayer-rules.ts、multiplayer-server.ts、multiplayer-client.ts | 依模式容量、房間協定、可靠輸入與序號 |
| web/lib/game.ts、web/app/page.tsx | 模式切入／退出、停止其他場景並恢復，不重複輪詢 |
| web/components/multiplayer-lobby.tsx、pvp-panel.tsx、web/app/globals.css | 固定房間、設定、戰鬥 HUD 與結算 |
| web/db/schema.ts、web/drizzle/ | 模式、倒數、串流與結果欄位的新增遷移 |
| tests/test_pvp_*.py、web/scripts/test-pvp-*.mjs | 規則、橋接、控制、HTTP 與回歸測試 |

**結構決策**：重用現有框架與工具；獨立狀態機避免 PvP 觸發 AI／城市／獎勵副作用。副本由 prepare 產生，根目錄與 web/public/rules 的模組內容必須一致。

## 階段與交付順序

1. 固定資料與協定，新增規則模組、橋接契約與測試入口。
2. US1 交付可獨立測試的房間與分隊 MVP；未接好戰鬥前僅本機驗證，不將半成品發布為可玩 PvP。
3. US2／US3 在固定核心上實作地面鎖定與飛行場景；共同檔案按任務順序修改。
4. US4 完成中止、重連、結果隔離；全流程通過後才進行整體驗收與發布。
5. 使用 quickstart 驗證，記錄真實結果；兩個 Git 根的 web 內容一致，GitHub PR 合併後依 Sites 正式流程建置、保存版本、發布與核對。

## 複雜度與例外記錄

| 選擇 | 必要理由 | 未採較簡單替代的原因 |
| --- | --- | --- |
| 獨立 PvP 核心／場景 | 真人飛行、固定能力、雙陣營及無存檔副作用 | 直接繼承合作會執行城市、空降與獎勵邏輯 |
| 串流換代與模擬租約 | 重連、舊局重送及房主背景凍結的明確契約 | online 布林與網路 heartbeat 不足以證明模擬仍推進 |
| 沿用房主權威 | 使用者最後明確選擇，保留現有部署 | 外部即時伺服器增加未要求的服務與帳號依賴 |

以上為設計取捨，已同步至 `docs/DECISIONS.md`；沒有新增第三方服務。
