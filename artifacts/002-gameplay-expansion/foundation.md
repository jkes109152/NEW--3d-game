# 共用基礎驗收

新版採封閉的 13 欄位 Profile、三免費武器、五個隔離欄位與十二類交易。原子保存先驗完整候選，再替換目標；PendingSave 保留同一候選，重試不重新交易。

已執行測試：test_catalog、test_profile_v2、test_transaction_v2、test_save_data、test_contracts、test_save_recovery、test_slot_isolation、test_save_v2_matrix。結果見 [測試日誌](tests.log)。未知版本、重複 JSON key、NaN、未知巢狀欄位、所有權錯誤、同 ID 異指紋、未來輪次、舊輪重送、備份失敗與刪除 token 均有行為斷言。

WORLD 共用地圖、掩體、出生區及通道；test_deployment、test_world_collision 與 test_rocket_collision 檢查有限座標、碰撞及可見性邊界。純規則測試不建立圖形引擎。
