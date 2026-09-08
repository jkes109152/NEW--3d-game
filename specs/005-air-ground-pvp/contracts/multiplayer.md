# 多人 PvP 介面契約

## 共通邊界

沿用 POST `/api/multiplayer`、現有 Cookie 身分、同站來源及 JSON 驗證。新行為限 mode=pvp 分支；建立房間未傳 mode 或舊房間資料缺 mode 時視為 coop。模式由已保存房間判定，後續請求不得覆寫。沿用 750000 字元整包及 20000 字元輸入上限，最多八份 PvP view；錯誤必須是繁體中文且非成功回覆。

請求與回覆均附 protocolVersion=1 於 PvP 資料。除 sync 初始化查詢外，每個已取得局次的操作含 roomId、runId（start 尚未產生 runId，依動作表）；交換另帶 inputStream、inputSeq、instanceId。輸入數字需有限、控制軸限制 [-1,1]，畫面比例 [0.2,6]；不接受客戶端位置、命中、耐久或 team 作為權威資料。

## 房間動作

| 動作 | PvP 請求 | 回覆與規則 |
| --- | --- | --- |
| create | name、mode=pvp | 建立容量八人房間，mode 只允許兩個已知值 |
| lobby | 無新增必要欄位 | 卡片新增 mode、capacity、count；count 含仍佔位且未退出的成員，不能以五秒 online 假裝有空位 |
| join | roomId | 只接受 waiting，原子限制八人；一人一次只能屬於一個房間 |
| sync | roomId、instanceId | 驗證成員後只查詢房間／本人 runId、currentStream、inputInstance 與 view，僅續連線 seen_at，不換串流、不續模擬租約；用於首次得知開局與重載初始化 |
| ready | roomId、ready | PvP 不傳 profile，服務端不使用存檔；僅 waiting 可修改 |
| start | roomId、instanceId | 僅房主；完整名單與 ready 版本須在條件式更新中再次檢查，Fisher–Yates 等機率抽選 ceil(N/2) 空中。回覆 runId、roster、startsAt、serverNow、timeLimitSeconds、自己的 inputStream |
| exchange | roomId、runId、instanceId、inputStream、inputSeq、input；房主另可送 snapshot、sequence | countdown 每 120 毫秒排程，playing 同頻率。拒絕非房主 snapshot、舊局、舊串流、無效角色資料；低序號操作不覆蓋。回覆 serverNow、完整房間摘要及本人 view；房主另取得下節定義的 hostInputs 與 departures |
| resume | roomId、runId、instanceId、expectedStream | 首次開局所有人（含同 instance 房主）可綁定串流；之後僅仍在十秒窗口內的非房主可換 instance 接回既有狀態。同 instance 重試冪等；房主新 instance 直接中止該局，不能重置損傷或時限 |
| finish | roomId、runId、instanceId | 僅原房主，先驗證逾時／instance，再從已儲存完整終局快照建立唯一 result，不信任額外客戶端 result；不寫 mp_results |
| abort | roomId、runId、instanceId、reason | 僅已認證房主可主動中止，reason 限 host_reload、simulation_gap、simulation_error、host_left；其他成員只能透過 exchange 觸發服務端超時判定 |
| leave | roomId、runId（在局時） | 等待室刪除成員；倒數取消開局；對戰中以原子交易寫入 departures 並刪除該房間成員資格；房主另中止且保留結果。成功後可立即加入別房，固定 roster 不刪除；終局可退出 |
| again | roomId、runId | 僅房主且 finished；先清理本房間十秒未連線的成員，再重設等待室；全員需重新準備，禁止計算下一關或發任何獎勵 |

任何成員請求先檢查房主模擬租約：countdown 起到 startsAt 以倒數時刻管理，playing 時十秒未收到 tick 前進即 aborted。收到舊 tick／單純 heartbeat 不更新 simulation_seen_at。逾時成員先原子寫入 departures 並釋放目前房間資格再回覆，後到 resume 不可復活。終局提交與 abort 採相同 run、狀態與版本的比較更新，只允許一次；已完成正常結果不得被後續房主離線改成中止。

## 操作格式與可靠性

input 包含 suspended、cancelThrough（取消至命令序號）、move_x／move_z、turn_x／turn_y、throttle、roll、look_total、aspect 與 commands。commands 是至多 96 筆 `{sequence,kind}`，kind 限 fire_down、fire_up、toggle_aim、jump；視角切換與設定屬本機，不送為戰場命令。空中只取飛行控制，地面只取移動／瞄準／發射／跳躍。滑鼠飛行時 turn_x／turn_y 為零，鍵盤飛行時不增加 look_total；切換模式先完成取消確認，避免兩種轉向疊加。地面不套用飛行設定的靈敏度或反轉。

look_total 為同串流累積滑鼠角度，以 inputAck.look_total 表示已消耗或取消值；離散命令保留到 inputAck.command_seq。以下 look_total_ack／command_ack 均為這兩個欄位的語意別名，不另傳第二份確認值。模擬每步限幅轉向並消耗期望轉角，一秒操作過期或 suspended 清除未消耗量，飛機不追趕舊滑鼠輸入。輸入串流初始化與改局清空舊命令；超量佇列停止輸入並提示重新連線，不能靜默丟失 fire_up。

## 權威快照與呈現

snapshot 含 mode=pvp、protocolVersion、runId、phase、tick、elapsed、result、views。views 必須恰好對應當局 roster，不得增添幽靈玩家。每份 view 含 selfId、team、tick、elapsed、actors、missiles、remainingSeconds、本人鎖定／冷卻、本人 inputAck、結果與事件環。完整角色包含已淘汰者及原因，不能只依瞬間事件通知。所有 view 的共同 actors／missiles／tick／elapsed／result 必須一致，各自私有的鎖定與確認不得串人；服務端拒絕彼此矛盾的八份世界。

服務端只回傳本人 view；view 內提供共同戰場實體和本隊觀戰資訊。淘汰角色不取得控制權；客戶端的觀戰對象限自己的存活隊友。事件按序號最多保留 128 筆並去重，只用於音效／脈動。

房主公布快照不是新的戰鬥權威服務：服務端做身分、局次、形狀、枚舉、數字與一致性驗證，但不宣稱防止房主造假。active 不能帶終局 result；finished 的 ground 勝需空中全滅，air 勝需 elapsed 已達 timeLimitSeconds 且仍有空中存活，或地面全退且仍有空中存活。reason 限 air_eliminated、timeout、ground_departed，必須與上述狀態及時間一致；aborted 必須 winner=null，拒絕提前以仍有飛機存活宣告 air 勝。

## Python／畫面橋接

`pvp_start({runId,roster,timeLimitSeconds})` 建立基礎世界；`pvp_tick({dt,frames,departedIds})` 回傳全部權威 view；`pvp_predict({actor,frames})` 只回傳本人的預測姿態；`pvp_dispose()` 清除當局。所有入口置於 `web/public/bridge.py`，與合作 party_* 分流。

地面 view 適配現有 AntiAirHud 的 weapon_category、fire_mode、aiming、lock_box_scale、lock_current、lock_valid、locks、aircraft、elapsed、fire_blocked、events 等欄位，camera 與規則投影使用相同 65 度垂直視角；只傳數字與已驗證識別，不把玩家名稱直接插入 HUD HTML。


## 初始化與取消輸入的補充契約

- 已有房間者先 sync 取得本人 runId／currentStream；首次開局與新分頁呼叫 resume 以 expectedStream 比較取得新的控制串流。沒有 runId 的等待室輪詢發現狀態轉換時只做 sync，不發送舊局輸入。已被換代的舊實例收到拒絕後停用控制並提示另一分頁已接管，不自動 resume 搶回。
- start 初始化每位成員 currentStream，inputInstance 可空；第一次 resume 綁定本頁 instance。同 instance 的重試冪等回覆，不再換代；新 instance 只能以目前 currentStream 比較換代。房主 instance 驗證優先於串流驗證，重載首張快照前仍會中止。
- suspended 包仍攜帶當前 look_total 與 cancelThrough，即使 commands 為空；房主對已收到但未消耗的輸入取消時，同步更新 look_total_ack 與 command_ack 至已丟棄水位，並清除射擊按住狀態。確認表示該輸入已處理或已取消，客戶端不再回放。
- 一秒過期亦取消房主已收到的控制量；更晚到但 sequence 較新的 suspended 包繼續前移取消水位。恢復包必須先完成取消確認再傳新控制，且需要新 fire_down；被取消的舊累積轉角／命令不能在恢復時補做。

## 房主輸入、時鐘與退出帳本

- 只有已認證且 instance 相符的房主可取得 hostInputs：每筆包含 playerId、inputStream、inputInstance、inputSeq、input、inputReceivedAt、lastSeenAt；涵蓋固定 roster 中尚未退出的成員。查詢同時限定 roomId 與 playerId，不能讀到該玩家新房間的操作。departures 為同局完整退出帳本；退出者不再出現在 hostInputs，但仍保留於 roster／views。非房主不可提交或覆寫這些伺服器欄位。
- serverNow、inputReceivedAt、lastSeenAt 與退出時刻使用同一伺服器毫秒時基。新控制包 inputReceivedAt 與 inputSeq 原子更新；初始或換代為空時視為 suspended。sync 只續 lastSeenAt；重送同序號不延長輸入有效性。有效 exchange 即使重送可續連線，但舊 instance／串流不得續租。
- 房主在收到回覆的本機單調時刻記錄 serverNow。每步以 serverNow 加收到回覆後的單調經過時間，計算 inputReceivedAt 的年齡；年齡大於等於 1000 毫秒即取消控制，取消水位不倒退。這是依伺服器接收時刻定義的一秒，並非客戶端取樣至網路送達的一秒；網路中的延遲另外由 SC-004／SC-005 驗證。不得以 online 布林或玩家自行上傳時間取代。
- 服務端在更新 seen_at 之前判斷：playing 非房主 lastSeenAt 相差大於等於 10000 毫秒即記 timeout；countdown 任一成員相差大於等於 1000 毫秒取消。截止值本身算逾時。房主在收到退出帳本的下一固定步套用 departedIds，不自行依網路估計永久退出；操作停用仍由房主逐步判定。
- 原子離開、逾時清理與 resume 都比對當前 roomId／runId／成員資格及 departures。重送 leave 對已記帳的同局玩家回覆成功，但不能刪除其新房間成員列；其餘舊局控制均拒絕。again 保留仍在本房間的成員，不把已離開者重新加入。

## 本機預測時間線與回放

- 權威快照 tick 表示已完成的 1/120 秒步數，elapsed 與 tick 一致；截止截短的最後一步只會出現在終局，不再預測。每份 view 明列 tick、elapsed 與本人完整可回放移動狀態。inputAck.tick 必須等於 view.tick；input_seq 只確認控制包，不能當作模擬步號。
- 第一次有效 view 建立本機時間線：以其 tick 為起點，從接收時刻以單調時鐘每 1/120 秒記錄一筆 PredictionFrame，tick 嚴格遞增。之後不因封包重送重新定時。收到較新權威 tick 時移除所有 tick 小於等於它的歷史，從該 actor 回放剩餘步；權威已超過本機時間線時直接前移基準，不能回放負時間。舊 tick 快照不回捲畫面。
- 回放透過同一 Python 移動函式依 tick 排序，每步只推進一次；從權威 actor 的未消耗轉角與確認水位起算，歷史中的累積 look_total 只補尚未納入的差值。已確認或取消的命令不重做，fire／鎖定／傷害一律不在預測計算。移動誤差在 100 毫秒內視覺收斂，大於 10 公尺直接校正；權威耐久、淘汰與勝負立即呈現。
- 記錄滿 120 步仍無新權威基準時，停止新增預測步，清空歷史、送 suspended 與取消水位並顯示「連線延遲，正在同步」。不截斷舊操作後繼續假裝已回放，也不自行中止全房。取得新有效 view 且取消確認完成才重建時間線，需重新按下控制。runId／stream 更換、淘汰或終局同樣清空歷史，舊確認不能解除新串流等待。
- 本機 tick 僅是有限視覺預測的時間對齊工具，不是要求房主補算客戶端過去位置。房主仍按自己的固定步使用最新有效控制；延遲造成的預測誤差以權威校正。以 30／60／144 格呈現、亂序／重複確認、500 毫秒延遲、120 步耗盡及換代取消測試核對回放次數與復原。
