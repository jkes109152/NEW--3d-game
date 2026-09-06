# 永久存檔契約 v1

每個欄位一個 UTF-8 JSON 檔案，預設位置為 `%LOCALAPPDATA%/AirDefenseQuality/slot-1.json` 至 `slot-5.json`。測試必須注入其他目錄。

## 允許的頂層欄位

```json
{
  "schema_version": 1,
  "coins": 0,
  "rebirth_count": 0,
  "max_aircraft_count": 2,
  "upgrade_levels": {},
  "upgrade_caps": {
    "max_hp": 5,
    "armor": 3,
    "aa_lock_time": 5,
    "aa_whitebox": 5,
    "weapon_cooldown": 5,
    "auto_defense_capacity": 5
  },
  "unlocked_weapons": ["ANTI_AIRCRAFT", "SNIPER", "PISTOL"],
  "rebirth_available": false,
  "last_completed_a_b": null,
  "profile_revision": 0,
  "operation_history": []
}
```

`max_aircraft_count` 與 `upgrade_caps` 是相容與顯示快照，不是可信的進度來源；載入後以 `rebirth_count` 與升級目錄推導。v1 頂層欄位集合是封閉的；未知欄位、未知 schema、錯誤型別、負金幣、無效 ID、重複武器或越過上限的資料必須拒絕。v1 不做猜測式資料遷移；未來資料遷移必須新增明確版本升級器與測試。

`operation_history` 每筆格式為：

```json
{
  "operation_id": "op-uuid",
  "kind": "purchase|reward|rebirth|save|failure",
  "request_fingerprint": "sha256-hex",
  "result_code": "applied|rejected|operation_conflict|failed_retryable",
  "profile_revision": 3,
  "summary": {"coins_delta": -250, "upgrade_id": "max_hp", "reason": "applied"}
}
```

`operation_history` 不淘汰，確保舊 operation ID 跨重啟仍冪等；fingerprint 不同時回傳 `operation_conflict`。

`failure` 記錄失敗後開放重生資格，與成功獎勵同樣以當局 ID 去重；不發放金幣。`summary.reason` 保存可顯示的細部結果碼（例如 `insufficient_coins`），重送時傳回原結果；`result_code` 保持上述四種分類。

## 寫入契約

- 序列化使用 UTF-8 JSON；禁止 pickle、eval 或任意物件反序列化。
- 先寫同目錄唯一暫存檔並 flush，再以原子替換提交；舊檔在提交成功前不得刪除。
- 損壞或未知版本先複製原始位元組到同一存檔目錄的復原備份，再顯示原因與重建確認；備份／寫入失敗時原檔保持可讀。
- 復原備份檔名為 `slot-N.corrupt.YYYYMMDDTHHMMSSZ.json`；若備份失敗，禁止建立新檔並回傳 `backup_failed`。
- 缺檔代表空欄位；建立新檔需要玩家明確選擇欄位，不得因讀取錯誤靜默覆蓋。
- 交易寫入使用 `operation_id`；重試同一 ID 回傳第一次結果，不重新扣金幣、發獎勵或增加重生次數。
- 刪除使用 `delete_operation_id` 與「刪除 → 確認」兩階段；確認只刪除選定 slot 的正式檔與該 slot 的備份／history，取消、重複確認或其他畫面輸入不得觸碰其他 slot。
- 同一執行緒序列化讀寫；寫入中的暫存檔只在原子替換成功後可見，並行讀取只能取得舊檔或完整新檔。

## 不得保存的資料

當局 HP、城市 HP、敵人／飛機／導彈／砲塔、武器冷卻、RPG 彈藥、鎖定進度、回血額度、未完成關卡、活動回呼與暫時 UI 全部在新局重建。
