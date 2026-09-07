# 002 本地程式碼審查與修正

日期：2026-09-07。審查基準為 main 的 `86a0b613b4701f95183a24abb26f6b790aed1001`，修正分支為 `002-review-fixes`。

使用者在本次審查前回報「人工測試完畢，都沒有問題」。此處記錄為使用者的整體測試回報；本次故障注入、深層 JSON 及確認期間檔案變更由自動測試另外驗證，未推定使用者已逐項測過。

## 範圍與評估

閱讀最近結算導覽差異及相連的 AppState、Controller、GameUI、交易與保存、準備與部署驗證；核對 [保存契約](../specs/002-gameplay-expansion/contracts/save-transactions.md)、[介面契約](../specs/002-gameplay-expansion/contracts/ui-deployment.md) 與相關測試。近期敗北回 1-1、勝利進入下一關準備的行為未發現新缺陷，既有回歸仍通過。

以下五項均有可重現的錯誤結果，判定需要修正，且已完成：

| 編號／優先度 | 觸發及原始影響 | 修正與依據 |
| --- | --- | --- |
| R1／P1 | 未擁有武器的預覽頁購買，替換存檔失敗後重試；回工坊時草稿仍為 None，畫面拋 TypeError。 | 一般保存與重試共用 Controller 草稿同步，新購武器從已保存所有權建立草稿。FR-029。 |
| R2／P2 | 工坊升級保存失敗，重試後擁有等級已增加，但預覽使用舊草稿等級；傷害文字與真正出戰能力不同。 | 同步升級及解鎖清單，保留未套用配件／外觀。W03 傷害一級搭重槍管為 1.4375，介面顯示 1.44。FR-008／009。 |
| R3／P2 | 損壞檔含 ±10^400 的部署座標，或 10000 層 JSON；OverflowError／RecursionError 逸出選檔列表，其他欄位也無法操作。 | 共用有限座標檢查，解析深度錯誤轉為既有 corrupt；原始位元組保留、備份後才能確認重建。有限但地圖外座標仍由準備撤回。FR-030。 |
| R4／P1 | 刪除視窗開啟後正式檔或備份已變更，token 僅綁欄位，舊確認仍刪除新內容與備份。 | token 記錄正式檔、備份清單及 SHA-256；確認時任何差異均失效，重新確認才可刪除。讀取失敗顯示訊息而不刪除。FR-030。 |
| R5／P1 | 復原視窗開啟後原檔被替換或移除；舊確認會重新備份新內容並建立空白檔。 | 確認時比對預覽的原檔雜湊，變更回 recovery_changed；重複舊確認也不能覆寫，須返回選檔重新確認。FR-030。 |

本次落實既有契約，不變更 Profile v2 結構、商品數值或結算規則；後續任務為 [T103–T106](../specs/002-gameplay-expansion/tasks.md)。

## 實際驗證

- 修正前新增 8 項回歸，共得到 8 個失敗與 6 個例外；[原始輸出](../artifacts/002-gameplay-expansion/code-review/tests-before.log) 留存。深層 JSON 初版深度未觸發解析限制，已提高到 10000 並驗證真實 RecursionError；另外載入基準提交的保存模組，[重現原版未處理例外](../artifacts/002-gameplay-expansion/code-review/deep-json-before.log)。
- 修正後 [33 項定向測試](../artifacts/002-gameplay-expansion/code-review/tests-targeted.log) 及最終 [145 項完整測試](../artifacts/002-gameplay-expansion/code-review/tests.log) 通過，compileall 退出碼 0。完整測試涵蓋結算重試、五欄位隔離、十二交易、暫停、戰鬥及保存；日誌尾端的套件安裝失敗字樣是啟動器故障注入測試的預期輸出。
- [1280×720](../artifacts/002-gameplay-expansion/code-review/1280x720/report.json) 與 [1920×1080](../artifacts/002-gameplay-expansion/code-review/1920x1080/report.json) 各 6 組離屏引擎情境、7 張截圖通過，使用實際 Button.on_click／Controller.input('enter')。檢查購買與升級重試、草稿套用、損壞復原、過期確認、重複回呼及重新確認刪除。
- 目視抽查兩解析度的工坊與過期確認畫面，能力、模型與錯誤訊息可讀。所有故障與刪除測試只操作 TemporaryDirectory；未讀寫正式玩家存檔。

## 修正後複查

重新閱讀四個程式模組的完整修改差異與測試，核對：重試不重算交易、草稿深拷貝保留選擇、普通購買仍更新所有權、破損備份可重新建立、錯誤欄位 token 不消耗其他欄位確認、成功刪除仍撤銷同欄位舊 token，以及結算保存後的游標與 UI generation 保護。未發現本次審查範圍內仍需修正的問題。

來源對照及命令退出碼見 [驗證摘要](../artifacts/002-gameplay-expansion/code-review/checks.json) 與 [LF 正規化來源 SHA-256](../artifacts/002-gameplay-expansion/code-review/source-sha256-lf.json)。文件連結、106 個任務及繁體中文另作核對。原生鍵鼠、音效主觀聆聽與 FPS 未在本輪重測；離屏結果不當作上述證據。檔案確認測試涵蓋使用者確認前的內容變更，不宣稱跨程序寫入具備原子互斥鎖。

GitHub 交付依憲章使用 gh，PR 實際合併與分支清理由 gh 遠端結果及交付回報確認，不能從預先撰寫的 PR 正文推定已合併。
