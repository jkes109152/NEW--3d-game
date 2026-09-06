# 音效與資產回退契約

## 音效事件

音效適配器接受 `weapon_fire(kind)`、`lock_progress`、`lock_complete`、`missile_launch`、`hit(kind)`、`explosion`、`enemy_hurt`、`air_raid_warning`、`level_success`、`level_failure` 與 `purchase_success/failure`。每類事件有音量匯流排與同時播放上限；超過上限依優先級丟棄最舊的非關鍵聲音，不阻塞模擬。

主音量、音效音量與靜音只影響播放，不影響判定、事件順序或測試結果。沒有音訊裝置或 WAV 載入失敗時，適配器回傳診斷事件並使用無聲實作。

## 資產 ID 與最低回退

資產登錄表至少包含 `aircraft_normal`、`aircraft_manpower_support`、`aircraft_fast`、`aircraft_boss`、`crew_normal`、`crew_boss`、`target_building` 與五個第一人稱武器。缺少可選網格（mesh）、紋理（texture）或著色器（shader）時，只替換該資產為自製幾何／基本材質，保留碰撞包絡、ID、比例與行為；不得把其他實例的材質狀態一併改色。

所有隨包外部資產在 `assets/LICENSES.md` 有來源、版本與授權；程序化模型與自合成 WAV 標為自製。繁體中文字型必須是隨包且授權明確的檔案，缺字不可只顯示系統回退方框。
