# US1 新檔與首局驗收

真實 Windows 鍵鼠由空欄位進入主選單，依裝甲、五槽武器、鳥瞰預覽與最終確認開始 1-1。零金幣、無裝甲、無塔、W01/W17/W03；從選檔至開戰 92.593 秒，符合 120 秒上限。原始事件見 [原生輸入紀錄](native-input-before.json)。

test_preparation、test_preparation_flow、test_story1_vertical 與 test_app_state 驗證草稿取消／返回、非法槽位、空槽、歷史部署撤回、保存前不建立 BattleState、失敗重試回確認頁及重新確認才開戰；首局重複結算只發一次獎勵，下一關需手動開始。結果見 [測試日誌](tests.log)。

免費武器實際透過公開 InputFrame 移動、瞄準與射擊，1-1 於 9.592 秒完成並取得 125 金幣；這是規則控制情境，不是人工通關。完整紀錄見 [經濟通關](economy.json)。
