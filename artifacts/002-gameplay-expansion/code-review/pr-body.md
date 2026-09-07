工坊購買或升級保存失敗後，重試可能使畫面崩潰或顯示舊能力；舊的刪除／復原確認也未驗證變更後的存檔內容。本次統一保存後草稿同步，保留未套用選擇，並讓過期確認保留新資料。異常巨大座標與深層 JSON 會回報損壞，仍可備份復原。

依據 [002 保存契約](https://github.com/jkes109152/NEW--3d-game/blob/main/specs/002-gameplay-expansion/contracts/save-transactions.md)、[介面契約](https://github.com/jkes109152/NEW--3d-game/blob/main/specs/002-gameplay-expansion/contracts/ui-deployment.md) 及 T103–T106；完整評估與限制見 docs/CODE_REVIEW_V2.md。Profile v2、商品數值及敗北回 1-1／勝利前往下一關規則維持原契約。

驗證：先重現失敗，再通過 145 項完整測試、compileall；1280×720／1920×1080 各 6 組實際離屏 UI 回呼情境及 7 張截圖通過，證據位於 artifacts/002-gameplay-expansion/code-review/。所有故障注入、復原及刪除只操作臨時存檔。使用者已在本輪開始前回報人工測試無問題。
