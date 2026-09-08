# PvP 驗證與執行指南

此指南描述 implement 階段應執行的程序；下列新測試檔尚待 tasks 建立。不得將命令清單視為已通過證據。

## 前提與隔離

在專案根目錄使用既有 `.venv`；網頁使用 `web/node_modules` 與 pnpm 鎖檔，不安裝或升級新依賴。測試身分、存檔與房間使用測試專用瀏覽器資料及本機 D1，不對正式網站建立測試玩家。保留使用者原本未提交的 artifacts 日誌。

## 本機準備與資料遷移

1. 在 `web/` 執行 `node scripts/prepare.mjs`，核對新增 pvp／pvp_motion 出現在 `public/rules/manifest.json` 且副本一致。
2. 在 `web/` 執行 `./node_modules/.bin/drizzle-kit.cmd generate`，核對僅新增最新 SQL／metadata，不改已套用遷移。
3. 在 `web/` 執行 `./node_modules/.bin/vinext.cmd dev --host 127.0.0.1`；使用實際輸出的 Local 網址，待本機頁面 HTTP 200。
4. 用專案既有本機 D1 測試連線套用新增遷移。wrangler 必須使用 vinext 實際生成的本機設定與 `--local`，不得省略成遠端操作；設定位置由本次 dev 輸出及產物確認。HTTP 測試腳本遇到缺表／欄位須失敗並明示，不自動接正式 DB。

## 規則、橋接及介面測試

在根目錄執行：

```powershell
& ./.venv/Scripts/python.exe -m unittest discover -s tests -p 'test_pvp_*.py'
& ./.venv/Scripts/python.exe -m unittest discover -s tests
```

在 `web/` 執行：

```powershell
node --experimental-transform-types --test scripts/test-pvp-controls.mjs scripts/test-pvp-client.mjs
node scripts/test-pvp-bridge.mjs
node --experimental-transform-types scripts/test-pvp-http.mjs
node scripts/test-multiplayer.mjs
pnpm test
& ./node_modules/.bin/tsc.cmd --noEmit
pnpm build
```

預期：新測試及既有單人／合作／fetch receiver 回歸全數通過；本機 HTTP 使用各自 Cookie 的二人和八人、七種時限、跨局／過時串流、非房主偽造拒絕；PvP 前後 mp_results 新增零筆且個人存檔內容相同。

## 真實流程與畫面

- 兩個獨立瀏覽器資料環境，完成名稱→PvP 房間→全員準備→隨機分隊→三秒倒數；地面瞄準實際玩家飛機，飛機可用兩套控制及 V 切視角。
- 比對飛機加減速／轉向與鏡頭，導彈沿自身前向飛行；測試鎖定、發射、兩次命中、撞毀、越界返回／淘汰、觀戰、時間結束與再戰。
- 在 960×640、1280×720、1920×1080 逐一檢查大廳、八人等待室、飛行設定、雙方 HUD 與結算，頁面與主要面板無垂直捲動，必要按鈕皆可見。
- 靜音與無音效裝置下仍顯示危險提示；指標鎖定失敗、失焦、Esc 設定與讀寫偏好失敗皆有可理解回饋。
- 由實際瀏覽器工具或人工操作取得畫面與輸入證據；遵守目前工具／Sites 使用限制。未獲取實際證據的項目標示未驗證，不能改以 HTTP 測試宣稱通過。

## 連線與生命週期

在本機測試專用傳輸層注入延遲／中斷，不改正式傳輸預設：200 毫秒往返測量雙方狀態一秒內對齊；500 毫秒延遲、重送與跳過快照不重複射擊或復活。完整兩人及八人各測正常結束與中止。

驗證 0.99／1.00 秒輸入停用、9.99／10.00 秒斷線與重連、尚無第一張快照的房主重載、已有快照重載、房主背景停頓超過一秒，以及十秒無模擬前進。正常結算後再斷線不得覆寫勝負。

反覆進出十次，核對只剩一份多人輪詢與當前場景的監聽／動畫，離開後無殘留導彈、HUD、Python 當局或持續音效；資源數不隨局次增加。

## 證據與發布

結果記於 `artifacts/005-air-ground-pvp/acceptance.md`：測試命令、日期、退出碼、測試人數、延遲設定、視窗、實測時間與證據檔案；沒有完成就列待辦。禁止保存正式 Cookie、憑證或玩家存檔至 Git。

確認所有規格與憲章關卡後：提交真實原始碼至 GitHub 工作分支、PR 合併與核對；web 自有 Git 提交與根目錄 web 子樹一致；依 Sites 技能以成功建置、推送後完整 SHA、驗證封裝保存新版本，再部署既有公開網址。新增遷移向後相容，回退前端不得刪除已部署資料欄位；失敗時保留舊版，明示部署狀態。

本次 tasks 文件生成不執行以上實作、測試或正式部署。
