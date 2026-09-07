玩家在較後關卡敗北後，原本「開始防守」仍重試原關；現在結算保存成功後回到 1-1，保留既有金幣與裝備。勝利結果的「返回主選單」改為「前往下一關（實際關卡）」，例如 2-3 勝利後顯示「前往下一關（3-1）」並直接進入該關出戰準備，確認配置保存後才開戰。最終關後顯示 1-1；Esc 保留返回主選單入口。

已同步 FR-024、US1 情境、計畫、數值／保存／UI 契約、README 與決策文件，追加 T099–T102。保存錯誤仍阻擋出戰，重試或舊按鈕連點不重發獎勵。

驗證：137 項測試、compileall 通過；兩解析度各 16 張離屏流程截圖與引擎按鈕／Enter／Esc 測試通過，回主選單後 15 項活動指標差異均為 0。已目視檢查核心結算畫面，未宣稱原生輸入或真人通關。[規格](https://github.com/jkes109152/NEW--3d-game/blob/main/specs/002-gameplay-expansion/spec.md) 與 [本次驗收](https://github.com/jkes109152/NEW--3d-game/blob/main/artifacts/002-gameplay-expansion/result-navigation/acceptance.md) 提供來源、命令與證據。
