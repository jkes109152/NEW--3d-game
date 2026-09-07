# 保存與交易契約

**版本**：002／Profile v2　**依據**：[資料模型](../data-model.md)、[數值表](../balance.md)

## 保存位置與相容性

- 預設 `%LOCALAPPDATA%/AirDefenseQualityV2/slot-1.json`～`slot-5.json`；偏好為同根目錄 `settings.json`。
- 測試／驗收可傳 `SlotRepository(root=絕對路徑)` 或 `AIR_DEFENSE_V2_SAVE_DIR`；明確 root 優先，其次新版環境變數，最後預設。不再讀取舊 `AIR_DEFENSE_SAVE_DIR`。
- 根目錄解析後若等於或位於舊 `%LOCALAPPDATA%/AirDefenseQuality` 內則拒絕，顯示「新版資料位置不能使用舊版資料夾」；不掃描或修改舊檔。測試使用臨時 LOCALAPPDATA 及分開的新舊根目錄驗證。
- 封閉 schema 恰含資料模型定義欄位。只接受版本整數 2；版本 1、99、bool、NaN、重複 JSON key、非 UTF-8、未知欄位或無效所有權皆拒絕；不偷偷轉換。
- 地圖失效部署與「目前不可出戰」配置交由準備流程處理，不能當整份檔案損壞；型別、ID、所有權或引用不合法仍為保存資料錯誤。
- 部署座標須能以有限浮點數表示；無法表示的巨大整數及超出 JSON 解析遞迴能力的資料，須回報損壞並保留原始位元組，不能使五欄位列表崩潰。一般有限但位於地圖外的座標仍依上一條撤回部署。

## 純規則與 repository 介面

- `new_profile(profile_id) -> ProfileV2`：建立三免費武器與預設配置。
- `validate_profile(data) -> ProfileV2`：驗完整形狀、型別、所有權與歷史；回深拷貝，不修改傳入值。
- `transact(profile, operation_id, request) -> TransactionResult`：僅計算與更新完整記憶體候選，不觸碰磁碟或引擎。
- `SlotRepository.transaction(slot, profile, operation_id, request)`：在現有 repository 鎖內計算、驗證並原子保存，回交易結果；IO 失敗回／拋可重試保存錯誤供 AppState 保存 PendingSave。
- `load/create/list_slots/save/prepare_recovery/recover/request_delete/cancel_delete/confirm_delete` 沿用既有功能入口，內部改驗 v2；slot 只接受整數 1～5。

`TransactionResult` 恰含 `result_code`、`reason`、`operation_id`、`profile_revision`、`coins_delta`、`summary`、`replayed`。result_code 為 applied、rejected、operation_conflict 或 failed_retryable；replayed 僅是當次回傳資訊，不新增歷史。 reason 是具體原因碼，不是新增 result_code：成功使用 ok，業務拒絕使用 already_owned／insufficient_coins／not_owned／incompatible／cap_reached／locked／not_eligible 或部署驗證原因；身分及輪次拒絕使用 profile_mismatch／stale_round／invalid_round。指紋衝突為 result_code=operation_conflict、reason=operation_conflict；IO 失敗為 result_code=failed_retryable、reason=save_failed，細部錯誤另由保存錯誤物件承載。非法請求結構回 rejected／invalid_request 且不記歷史。所有未套用回傳 coins_delta=0；重播沿用原結果摘要。

## 交易請求

每筆 request 共通必填 `kind`、`profile_id`、`rebirth_count`。各種類的額外欄位如下，拒絕未列欄位；UI 不傳價格、傷害或退款數值。

| kind | 額外欄位 | 結果 |
| --- | --- | --- |
| purchase_weapon | weapon_id | 未擁有的付費武器進庫存，零升級原色素面 |
| purchase_armor | armor_id | 增加一種裝甲所有權 |
| purchase_turret | turret_id | r≥1 才可購買，建立 turret-操作ID；每筆操作一台 |
| upgrade_player | upgrade_id，僅 max_hp | 自身血量等級加一 |
| upgrade_weapon | weapon_id、upgrade_id | 只改適用且已擁有武器的一項等級 |
| purchase_attachment | weapon_id、attachment_id | 解鎖該武器相容配件，不自動選用 |
| purchase_cosmetic | weapon_id、cosmetic_kind、cosmetic_id | cosmetic_kind 僅 color／pattern；只解鎖該武器 |
| customize_weapon | weapon_id、selected_attachments、selected_color、selected_pattern | 一次免費選用已擁有項目，不能修改出戰槽 |
| confirm_loadout | loadout | 完整保存裝甲、五槽、部署，金額不變 |
| reward | a、b、A | 驗證當輪 A=2+r，以公式發獎勵及更新歷史與資格 |
| failure | a、b、A | 驗證本關，設定資格，不發金幣 |
| rebirth | 無 | 完整重置並保留歷史；金幣全歸零 |

總共 12 種業務交易。一般保存重試不是另一筆交易，不另追加 save 歷史。

`summary` 固定含 coins_delta；購買／升級另含對應商品 ID 與 new_level（若適用），砲塔購買含 instance_id，自訂含 weapon_id，配置含 deployed_count，reward／failure 含 a、b、A，重生含 previous_rebirth_count、new_rebirth_count。拒絕只含 coins_delta=0，不接受任意摘要欄位。

## 驗證與防重複順序

1. 驗 operation_id、請求形狀與型別；非法結構不改任何資料或歷史。
2. profile_id 必須等於正在操作的欄位身分，否則回 result_code=rejected、reason=profile_mismatch 且不寫入歷史。
3. 以排序鍵、UTF-8、禁止 NaN 的 canonical JSON 算 SHA-256；同 operation_id／同指紋回原結果，不能重新套用。不同指紋回 operation_conflict，資產、revision 及歷史不變。
4. 新操作的 rebirth_count 必須等於目前輪次；舊輪次回 result_code=rejected、reason=stale_round；未來輪次回 result_code=rejected、reason=invalid_round 且不追加歷史，以免保存尚未存在的輪次。再驗所有權、相容性、前置、上限、完整配置與金額。
5. 套用於深拷貝；業務拒絕（含 stale_round）也追加一次 rejected 紀錄，revision 加一，但資產與金幣不變。同 ID 後續回原拒絕結果。
6. 驗完整候選、替換記憶體並保存；歷史保存請求輪次、指紋與原結果。重生後保留所有紀錄，不依紀錄重新發商品。

重購已擁有武器／裝甲／配件／外觀回 result_code=rejected、reason=already_owned，不扣款；選用目前相同自訂或相同配置可回 applied、coins_delta=0。新操作 ID 的塔購買是另一台，沒有隱藏庫存容量上限。

reward／failure 只能由 AppState 對持有的結束中 AttemptId 結算，不由商店或其他 UI 路由發送；a、b、A 必須吻合該當局。操作 ID 使用該 AttemptId，成功與失敗競爭不能各結算一次。

## 保存失敗與恢復

- 保留同目錄暫存→flush／fsync→os.replace，舊目標在替換成功前保持完整；例外清理只能移除本次暫存。
- 任一交易寫入失敗，AppState 保留完整 candidate、原 operation_id／result、來源路由及成功後續動作，進 save_error。不能繼續戰鬥、交易、重生、換檔或關閉視窗丟棄候選；顯示重試與原本錯誤原因。
- 重試直接保存完整候選，不重跑 transact。購買／自訂成功回原商品頁，結果結算回結果畫面，重生回主選單，配置回 prepare_confirm；每個後續動作最多執行一次。
- 若未保存便強制終止程式，重啟只載入原磁碟版本，不宣稱候選已保存。測試需區別正常重試與程序中斷。
- 損壞資料沿用先備份原始位元組與雜湊、使用者確認後重建；原檔已變或備份失敗則不重建。未知版本亦保留原檔。
- 刪除 token 綁定 slot、目標內容與 UI 世代，取消或過期不刪資料；刪除新欄位不接觸舊版欄位。

2026-09-07 本地審查補充：復原確認須比對預覽時原檔雜湊，原檔被替換或移除時回報 recovery_changed，要求返回選檔重新確認；連按舊確認不能接受新內容。刪除確認比對正式檔與此次將刪除的備份清單及各檔雜湊，任一內容或清單變更均使 token 失效。讀取確認內容失敗時顯示錯誤訊息並保留資料。UI 世代仍由既有按鈕 generation 防止舊畫面回呼。

## 必要驗收

五欄位的所有商品／配置往返保存、雙同型塔身分、重生全部清空、上輪已套用及未套用請求、相同 ID 不同請求、每類交易的替換失敗與重試、未知版本、損壞備份、取消刪除及舊檔 bytes／mtime 不變，均須有實際執行測試。設定保存與商品交易分開，重生不能清掉 settings.json。

## 敗北關卡重設（2026-09-07 修訂）

failure 的請求／歷史摘要仍使用實際敗北當局的 a、b、A；保存完成的 continuation 將執行中 cursor 改為 1-1。保存失敗保留完整 PendingSave，仍阻擋出戰及返回選單；重試成功才套用同一個重設，不再套用交易或清除已購成果。reward 仍只在保存成功後推進下一關，勝利按鈕不能繞過此關卡。
