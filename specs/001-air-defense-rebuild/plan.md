# 實作計畫：3D 防空守衛完整重建

**分支**：`001-air-defense-rebuild` | **日期**：2026-09-05 | **規格**：[spec.md](spec.md)

## 摘要

從空白專案完整重建單機 Windows 第一人稱 3D 防空遊戲。實作先建立不依賴圖形引擎的規則核心，再接上 Ursina／Panda3D 場景、輸入、HUD、音效與自製資產；所有持久交易以可驗證的 JSON schema（結構描述）與 `operation_history` 操作歷史保護，所有 T01～T22 以固定時間／亂數或真實畫面證據驗收。

## 技術背景

**語言／版本**：Python 3.12.x；主要驗證環境 Python 3.12.13，啟動器只接受 Python 3.12.x 並在依賴安裝前檢查版本。

**主要依賴**：`ursina==8.3.0`、`panda3d==1.10.16`；遊戲規則只用 Python 標準庫；測試使用標準庫 `unittest`、`compileall` 與自製測試固定資料，不把 pytest 加入正式依賴。

**儲存**：`%LOCALAPPDATA%/AirDefenseQuality/slot-1.json` 至 `slot-5.json` 的 UTF-8 JSON；獨立 `settings.json` 保存品質設定；測試注入暫存 Profile 根目錄。Profile v1 包含永久 `operation_history` 操作歷史以支援跨重啟冪等。

**測試**：`unittest` 純規則／整合測試、compileall 語法檢查、引擎 import／最小視窗冒煙測試、正常輸入垂直切片、T01～T22 驗收矩陣、指定解析度截圖與 FPS／生命週期量測。

**目標平台**：Windows 10+、64 位元桌面、1280×720 與 1920×1080；無音訊裝置、可選資產缺失與低畫質仍需可進入核心遊戲。

**專案類型**：離線桌面遊戲，具備本機啟動器與純 Python 規則函式庫。

**效能目標**：A=4、中畫質、1280×720 暖機 10 秒後量測 60 秒，平均 FPS >=55、P1（最差 1%）frame time 對應 FPS >=45、不得出現連續兩個以上 frame time 超過 250 ms 的持續卡頓；A=8／6 台砲塔與空地敵人壓力場景連續量測 60 秒、以 1 秒取樣時，投射物／特效活動計數不得呈單調增加，結束後與基準差異為 0。

**約束**：保留附件的核心數值、操作、戰役、商店與重生契約；離線遊玩；依賴只在專案 `.venv`；不可依賴私人模型、未授權素材、系統 PATH、PowerShell ExecutionPolicy 或公開遠端；測試不可讀寫正式玩家存檔。

**規模／範圍**：A=2 首次戰役 7 關，生成器至少驗證到 A=19；每場支援多機、多目標鎖定、6 台砲塔與空地敵人；五個 Profile、十項升級、五種武器、四種飛機、一般敵兵與地面 Boss。

## 憲章檢查 — 設計前

| 關卡 | 結果 | 證據 |
|---|---|---|
| 產品契約一致性 | 通過 | `spec.md` FR-001～FR-031 與附件數值；無新增多人／登入／付費範圍 |
| 先建立可決定規則 | 通過 | `data-model.md` 的純規則模型、固定 1/120 tick、注入亂數種子／時鐘 |
| 以證據驗證品質 | 通過 | `acceptance-matrix.md` 逐項對應 T01～T22，另要求截圖與 FPS 證據 |
| 安全持久化與冪等操作 | 通過 | v1 JSON、封閉 schema、原子替換、跨重啟 `operation_history` |
| 可用品質與誠實回退 | 通過 | 啟動器／UI／音效／資產契約與缺失能力回退 |

沒有需要以複雜度例外放行的違反項目。

## 架構與資料流

1. `main.py` 建立應用程式、時鐘、Profile 儲存庫、場景適配器、UI 與音效適配器；只負責生命週期與路由。
2. `state.py` 維護 `BattleState`、畫面狀態、attempt_id 與 pause／teardown；`progression.py` 產生關卡、獎勵、升級、回血、重生與商店結果。
3. `combat.py` 實作攻擊前驗證、鎖定、命中事件、距離契約、RPG 去重、導彈掃掠與 Boss 砲塔下限；`entities.py` 保存純資料與移動／AI規則。
4. 每幀輸入轉成 `InputFrame`；模擬適配器以固定 tick 回傳狀態快照與有序事件；`scene.py` 將事件映射為 3D Entity、碰撞器（collider）、粒子與鏡頭回饋。
5. `ui.py` 只依快照渲染 HUD／選單並派送輸入；`audio.py` 只消費音效事件；缺失裝置／資產不阻斷規則 tick。
6. `save_data.py` 以 Profile v1 schema 驗證、`operation_history` 操作歷史、同目錄暫存與原子替換提交；交易先產生結果，再以同一 `operation_id` 重試。

## 公開介面與型別

- **Profile schema 契約**：[contracts/save-schema.md](contracts/save-schema.md) 定義封閉頂層欄位、`operation_history`、備份命名、刪除確認與錯誤語意。
- **模擬介面**：[contracts/simulation-adapter.md](contracts/simulation-adapter.md) 定義 `InputFrame`、`SimulationStepResult`、事件排序與 attempt_id 隔離。
- **UI 契約**：[contracts/ui-state.md](contracts/ui-state.md) 定義畫面狀態、輸入優先順序、HUD 分區、準心互斥與商店 ID 映射。
- **音效／資產契約**：[contracts/audio-assets.md](contracts/audio-assets.md) 定義音效事件、播放上限、資產登錄表與回退。
- **啟動器契約**：[contracts/launcher.md](contracts/launcher.md) 定義 `start_game.cmd`、`run_tests.cmd` 的路徑、環境、日誌與退出碼。

## 實作階段與關卡

### 第 1 階段 — 純規則與存檔

- 建立 config、型別、`LevelDefinition`、戰役公式、獎勵、十項升級、HP／鎧甲／回血、重生與商店交易。
- 建立封閉 Profile v1、`operation_history`、損壞備份、原子替換、五欄位隔離與故障注入測試固定資料。
- 先通過 T01～T04、T15～T20 的純 Python 測試，再進入引擎。

### 第 2 階段 — 戰鬥垂直切片

- 建立固定 tick、InputFrame、單架普通飛機、單目標鎖定／導彈、下降／地面敵兵、手槍與完成結算。
- 接上第一人稱鏡頭、碰撞測試固定資料、掩體遮擋與 HUD；以實際滑鼠／鍵盤走完 1-1。
- 通過 T05～T07、T10～T12 與一輪正常輸入截圖後，才擴充全部內容。

### 第 3 階段 — 完整戰役與戰鬥系統

- 加入四種飛機、支援／Boss 下降批次、快速飛機驗證、狙擊／RPG／多目標炮、砲塔與空地混合戰。
- 完成 A=2 七關、A>=3 生成、Boss 最低血量、RPG 半徑、所有武器關卡與一次性事件清理。
- 通過 T08～T14、T21，並保存多目標齊射與空地混合戰畫面。

### 第 4 階段 — UI、音效、資產與設定

- 完成五存檔選擇、主選單、十項商店、重生確認、結果、兩種瞄準模式、設定與完整 HUD。
- 建立程序化自製模型、可攜繁中字型、自合成 WAV、粒子／尾焰／命中／爆炸的有限壽命與資產回退。
- 以 1280×720／1920×1080、視窗／全螢幕、中文路徑與失焦完成 T19、T22 及畫面證據。

### 第 5 階段 — 啟動、效能與交付

- 實作 `start_game.cmd`／`run_tests.cmd`、依賴固定、錯誤日誌與離線後續啟動；建立 `requirements-game.txt`，精確釘選 Ursina／Panda3D。
- 使用 `tools/performance_probe.py` 量測 A=4 60 秒、A=8 壓力 60 秒與十次生命週期；A=8 以 1 秒取樣檢查投射物／特效活動計數不呈單調增加且結束回到基準；依資料調整物件池（object pool）、共享幾何、粒子／陰影品質，不限制 A 或鎖定數作弊。
- 產生 `docs/SPEC.md`、`PLAN.md`、`TASKS.md`、`DECISIONS.md`、`ACCEPTANCE.md`、`assets/LICENSES.md` 與 `artifacts/`，執行 converge 對照全部需求。

## 專案結構

```text
air_defense/
├── __init__.py
├── main.py              # 應用程式組裝、生命週期與啟動
├── config.py            # 常數、數值、色彩、品質設定
├── state.py             # AppState、BattleState、畫面與 pause／teardown
├── progression.py       # 關卡、金幣、升級、回血、重生、交易
├── combat.py            # 武器、鎖定、距離、命中、傷害與導彈
├── entities.py          # 純資料、飛機、敵兵、砲塔、路線規則
├── scene.py             # Ursina／Panda3D 場景、碰撞、鏡頭、資產
├── ui.py                # 選單、HUD、商店、設定與輸入映射
├── audio.py             # 音效事件、匯流排、上限與無聲回退
└── save_data.py         # JSON schema、備份、原子保存、復原
assets/
├── models/ textures/ audio/ fonts/
└── LICENSES.md
tests/
├── test_*.py（規則、狀態、契約與各使用者故事測試）
└── fixtures/
tools/
├── performance_probe.py
└── package_project.ps1
docs/
├── SPEC.md PLAN.md TASKS.md DECISIONS.md ACCEPTANCE.md
artifacts/
specs/001-air-defense-rebuild/
├── spec.md plan.md research.md data-model.md acceptance-matrix.md
├── quickstart.md contracts/
└── checklists/requirements.md
requirements-game.txt
start_game.cmd
run_tests.cmd
README.md
```

**架構決策**：選擇單一 Python 桌面專案；純規則模組與引擎／UI／音訊適配分離，讓 T01～T20 不需視窗即可跑，並讓 T21～T22 可對應真實生命週期與回退。`specs/` 保存 SDD 產物，`docs/` 保存與最終交付同步的繁中說明。

## 驗證計畫

- 每完成一個階段執行其關卡與受影響 T 編號；所有失敗保留原始輸出，不以源碼字串或函式存在推論通過。
- `quickstart.md` 定義首次啟動、垂直切片、解析度／輸入、效能與十次生命週期；`acceptance-matrix.md` 驗收矩陣定義 T01～T22 的固定輸入與證據。
- 原生視窗不可用時，將純規則、引擎匯入、資產登錄表與無視窗回退標為已驗證，將滑鼠／截圖／FPS 標為未驗證；不得把自動情境當成實際輸入。
- `tools/performance_probe.py` 必須記錄暖機 10 秒、量測 60 秒、平均 FPS、P1（最差 1%）frame time 對應 FPS、連續兩個以上超過 250 ms 的 frame time 卡頓、硬體／解析度／畫質與十次生命週期基準差異。
- 完成實作後執行 `$speckit-converge`，補上規格與程式仍有差異的 tasks，再更新 `docs/ACCEPTANCE.md`。

## 憲章檢查 — 設計後

| 關卡 | 結果 | 設計後證據 |
|---|---|---|
| 產品契約一致性 | 通過 | T01～T22 矩陣、固定商店／武器／戰役數值與明確範圍 |
| 先建立可決定規則 | 通過 | 資料模型的固定 tick、seed、事件優先序、純規則套件 |
| 以證據驗證品質 | 通過 | 快速開始、驗收矩陣、截圖／FPS／清理計數規則 |
| 安全持久化與冪等操作 | 通過 | 封閉 schema、跨重啟 `operation_history`、故障注入與原子保存 |
| 可用品質與誠實回退 | 通過 | 啟動器、UI、音效／資產回退、中文／無網路路徑契約 |

所有關卡通過，沒有待解決的需求釐清標記或需要記錄的複雜度例外。

## 複雜度追蹤

無憲章違反，故不需要複雜度例外表。
