# PvP 資料模型

## 既有資料的擴充

採新增遷移，保留已發布的 0000–0002 SQL 與所有既有 metadata。以 `web/db/schema.ts` 為定義來源，使用現有 drizzle-kit 生成下一份 SQL 與 metadata；實作前核對是否已有更新的遷移，不假定固定檔名。

### 房間 mp_rooms

保留既有欄位並新增：

| 欄位 | 型別／預設 | 語意 |
| --- | --- | --- |
| roster_revision | 整數，預設 0 | 加入、離開、準備或清理等待成員時遞增，start 以此版本再次比對 |
| mode | 文字，非空，coop | 只接受 coop 或 pvp；容量由模式推導，不能由使用者自訂 |
| starts_at | 整數或空 | 伺服器毫秒時刻，countdown 起點加三秒 |
| time_limit_seconds | 整數或空 | 依當局總人數表推導，不接受客戶端值 |
| host_instance_id | 文字或空 | 房主本次頁面載入的識別，start 時固定 |
| simulation_seen_at | 整數或空 | 最後成功接受更大模擬 tick 的伺服器時間 |
| simulation_tick | 整數，預設 0 | 與網路快照 sequence 分開，防止同一模擬畫面反覆續租 |
| result | JSON 文字或空 | PvP 終局結果；不產生合作收據 |

status 在原 waiting、playing、finished、closed 之外新增 countdown。PvP 正常與中止都進入 finished 並保留 result；空等待室可 closed。PvP roster 為固定 `{id,name,team}` 陣列，不含 profile。合作 roster 不變。

### 成員 mp_members

新增 `input_stream`、`input_instance`（可空文字）及 `departed_at`（可空毫秒整數）。原 input_seq 仍為同串流遞增序號，seen_at 為伺服器最後連線時刻。PvP 進行中退出不刪除成員列，改記 departed_at；再次開局前移除退出成員。既有合作流程不變。

resume 使用 expectedStream 條件比對，產生新 input_stream 並清空舊輸入。相同 input_instance 的重試傳回原串流，不再換代；過時的 expectedStream 拒絕。新局全部輸入與串流重新初始化。逾時退出者不得 resume 復活。

## Python 當局資料

- `PvpBattle`：run_id、固定 roster、phase（active／finished／aborted）、elapsed、limit、tick、actors、missiles、result、事件序號。倒數由房間負責，倒數未完成不推進戰鬥。
- `GroundActor`：player_id、position、yaw／pitch、垂直速度、aiming、鎖定目標／進度／有效性、下次發射時刻、擊落數、連線狀態、輸入確認。
- `AirActor`：player_id、position、yaw／pitch／roll、speed、hp=2、越界經過時間、淘汰原因／時間、輸入確認。所有數值有限，單位公尺、秒、度。
- `PvpMissile`：當局唯一 id、owner_id、target_id、position、forward、age；傷害與速度等使用 spec 基礎武器契約。
- `InputAck`：stream、input_seq、command_seq、look_total；清楚區分已收到與已處理操作；已處理包含已模擬或取消，取消前移確認水位，供預測校正且禁止回放舊輸入。
- `PvpResult`：runId、winner（ground／air／null）、reason、elapsed、players（id、name、team、alive、kills、eliminationReason）。winner=null 僅用於 aborted。結果確定後不可覆寫。

## 狀態轉移與優先順序

1. waiting → countdown：2–8 人全員準備、開始名單原子確認、服務端抽選，建立 runId 與 startsAt。
2. countdown → waiting：成員退出或一秒無新心跳，清除 ready／run／分隊。倒數舊包一律失效。
3. countdown → playing：到 startsAt 且名單仍有效，配發基礎角色，elapsed=0；同步初始狀態可早於開始時間發布，但不得累積飛行或鎖定。
4. playing → finished：房主先處理連線退出與中止，再推進至截止時刻內的移動／命中／淘汰，最後判斷地面全退、空中全滅或時間結束。雙隊全退／房主失效優先 aborted。
5. finished → waiting：房主 again；保留在線成員名稱，移除退出成員，重置 ready／輸入／結果，下一局重新抽選。
6. active 角色 → eliminated 或 departed：單向不可逆；觀戰只切換目標，不建立新角色。空中全滅為 ground 勝，地面全退為 air 勝。

## 本機偏好與隔離

新增獨立鍵 `candy-defense-web:pvp-controls:v1`，包含 version=1、mode=mouse／keyboard、sensitivity=0.2–3、invertY、camera=chase／cockpit。壞值回預設並提示，不改寫玩家存檔；儲存失敗保留本次設定於記憶體並明示未保存。靜音沿用既有全域偏好，不另創互相衝突開關。
