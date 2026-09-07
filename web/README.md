# 糖果防線網頁版

此目錄為 Sites 部署專案。遊戲原本的 Python 規則以 Pyodide 執行，Three.js 僅負責畫面。

- pnpm install：安裝依賴。
- pnpm dev：準備同源執行環境與素材，啟動預覽。
- pnpm test：執行 8 組輸入控制、7 組網頁適配回歸，以及 Pyodide 核心流程與保存邊界測試。
- pnpm build：建立 Cloudflare Worker 與客戶端資源。

scripts/prepare.mjs 在桌面專案中同步純規則及素材；獨立部署儲存庫使用已保存的 public/rules 與音效。public/runtime 由已鎖定的 pyodide 套件重建。

存檔只存在玩家瀏覽器，以 origin 隔離；不送往伺服器。詳細驗證範圍見上層 specs/003-web-deployment/spec.md。

遊玩方法可由頂部按鈕或 H 開啟，戰鬥中開啟會暫停。出戰先停在就緒畫面，可選滑鼠視角、鍵盤視角或觸控；滑鼠捕捉失敗可切換鍵盤模式。操作提示与綁鍵共用 lib/controls.ts，報價與戰鬥 HUD 使用原 Python 規則的即時結果。

觸控區只處理自己的 pointer；移動、轉向與射擊可以同時使用，釋放或取消單指不會清除其他指頭。暫停會清空輸入，恢復先送 release，防止舊的持續射擊帶入新狀態。畫面 generation 與資料 revision 拒絕過期導覽／交易。
