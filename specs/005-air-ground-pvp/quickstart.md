# PvP 驗證與執行指南

此指南對應已建立的實作與測試入口；實際結果見 [驗收紀錄](../../artifacts/005-air-ground-pvp/acceptance.md)。命令清單本身不代表已通過，滑鼠原生操作仍須完成實際驗收。

## 前提與隔離

在專案根目錄使用既有 `.venv`；網頁使用 `web/node_modules` 與 pnpm 鎖檔，不安裝或升級新依賴。測試身分、存檔與房間使用測試專用瀏覽器資料及本機 D1，不對正式網站建立測試玩家。保留使用者原本未提交的 artifacts 日誌。

## 本機準備與資料遷移

1. 在 `web/` 執行 `node scripts/prepare.mjs`，核對新增 pvp／pvp_motion 出現在 `public/rules/manifest.json` 且副本一致。
2. 本次新增遷移為 `drizzle/0003_nappy_skin.sql`，已由 drizzle-kit 生成。新 checkout 不必重新產生；只有修改 schema 才執行 `./node_modules/.bin/drizzle-kit.cmd generate`，核對僅新增 SQL／metadata，不改已套用遷移。
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
node --experimental-transform-types --test scripts/test-pvp-room.mjs scripts/test-pvp-hud.mjs scripts/test-pvp-controls.mjs scripts/test-pvp-client.mjs
node scripts/test-pvp-bridge.mjs
node --experimental-transform-types scripts/test-pvp-http.mjs
node scripts/test-multiplayer.mjs
pnpm test
& ./node_modules/.bin/tsc.cmd --noEmit
pnpm build
```

上述四支 Node 測試已註冊為 `test:pvp:unit`，橋接為 `test:pvp:bridge`、HTTP 為 `test:pvp:http`；`pnpm test:pvp` 依序執行三者，任一失敗回傳非零。Python 測試仍由根目錄命令執行。

HTTP 測試先以假時鐘、真實 SQL 遷移與獨立 Cookie 檢查邊界，再載入 `test-pvp-transport.mjs` 啟動僅綁定回環位址的真實 HTTP 服務。後者量測二人／八人、200／500 毫秒延遲、跳包、重送與結果一致性；另以固定位置靶機隔離運動，透過真實鎖定／導彈規則量測追蹤、鎖定與傷害資料傳遞。這些測試不替代真人飛行操作驗收，也不接受正式網址。

預期：新測試及既有單人／合作／fetch receiver 回歸全數通過；本機 HTTP 使用各自 Cookie 的二人和八人、七種時限、跨局／過時串流、非房主偽造拒絕；PvP 前後 mp_results 新增零筆且個人存檔內容相同。

## 真實流程與畫面

- 兩個獨立瀏覽器資料環境，完成名稱→PvP 房間→全員準備→隨機分隊→三秒倒數；地面瞄準實際玩家飛機，飛機可用兩套控制及 V 切視角。
- 比對飛機加減速／轉向與鏡頭，導彈沿自身前向飛行；測試鎖定、發射、兩次命中、撞毀、越界返回／淘汰、觀戰、時間結束與再戰。
- 在 960×640、1280×720、1920×1080 逐一檢查大廳、八人等待室、飛行設定、雙方 HUD 與結算，頁面與主要面板無垂直捲動，必要按鈕皆可見。
- 靜音與無音效裝置下仍顯示危險提示；指標鎖定失敗、失焦、Esc 設定與讀寫偏好失敗皆有可理解回饋。
- 指標鎖定無法取得時可改鍵盤模式；地面追加方向鍵轉向、Q 切換瞄準、F 發射，飛行仍依原方向鍵／W／S／Q／E／V 規則。回退可用不代表滑鼠模式已完成驗收。
- 由實際瀏覽器工具或人工操作取得畫面與輸入證據；遵守目前工具／Sites 使用限制。未獲取實際證據的項目標示未驗證，不能改以 HTTP 測試宣稱通過。

## 連線與生命週期

在本機測試專用傳輸層注入延遲／中斷，不改正式傳輸預設：200 毫秒往返測量雙方狀態一秒內對齊；500 毫秒延遲、重送與跳過快照不重複射擊或復活。完整兩人及八人各測正常結束與中止。

驗證 0.99／1.00 秒輸入停用、9.99／10.00 秒斷線與重連、尚無第一張快照的房主重載、已有快照重載、房主背景停頓超過一秒，以及十秒無模擬前進。正常結算後再斷線不得覆寫勝負。

另驗證 sync／同序號重送不延長 input_received_at、舊串流不能續連線、房主 hostInputs 含正確時刻；玩家退出後立即加入／建立別房、舊局遲到 leave 不刪除新資格且舊輸入不可控制新局。預測測試涵蓋固定步回放、亂序確認、取消水位與 120 步滿載後恢復。

反覆進出十次，核對只剩一份多人輪詢與當前場景的監聽／動畫，離開後無殘留導彈、HUD、Python 當局或持續音效；資源數不隨局次增加。

需要一個瀏覽器與獨立房主進行畫面驗收時，在 `web/` 執行 `node scripts/pvp-local-host.mjs 2` 或 `8`。腳本只連接 localhost:3000，保留一格給瀏覽器；其他玩家持續提交飛行或瞄準操作，全部準備後開始，結果八秒後返回等待室。`--lifecycle` 將結果停留縮短為 0.2 秒，僅供反覆進出。身分與 Cookie 只留在程序記憶體，測試結束須離開房間並停止腳本。`read_defense_status` 的 PvP 區段可唯讀取得角色、鏡頭、監聽數、幾何資源與近期平均畫面更新率。

## 證據與發布

結果記於 `artifacts/005-air-ground-pvp/acceptance.md`：測試命令、日期、退出碼、測試人數、延遲設定、視窗、實測時間與證據檔案；沒有完成就列待辦。禁止保存正式 Cookie、憑證或玩家存檔至 Git。

確認所有規格與憲章關卡後：提交真實原始碼至 GitHub 工作分支、PR 合併與核對；web 自有 Git 提交與根目錄 web 子樹一致；依 Sites 技能以成功建置、推送後完整 SHA、驗證封裝保存新版本，再部署既有公開網址。實作 PR 合併／分支清理後，部署證據使用從最新 main 建立的 005 文件分支另送 PR，核對合併並清理；不直接提交 main。新增遷移向後相容，回退前端不得刪除已部署資料欄位；失敗時保留舊版，明示部署狀態。

正式發布前仍須逐項確認 tasks 的未勾選驗收，不以程式已存在或草稿 PR 已建立宣稱正式上線。
