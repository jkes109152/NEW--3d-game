# UI、輸入與畫面狀態契約

## 頂層畫面狀態

```text
slot_select → profile_menu
profile_menu → battle_setup → battle
battle ↔ pause_menu
battle → result_success / result_failure → profile_menu
profile_menu → store / rebirth_confirm / settings
```

每個畫面只有一個活動根節點；離開畫面先銷毀暫時按鈕、輸入回呼與計時器。Esc 在戰鬥進入暫停，在其他畫面返回上一層；Enter 在選單觸發目前焦點按鈕；Space 僅在主選單可作為開始快捷鍵。

## HUD 狀態

HUD 讀取模擬適配器的快照，固定分區如下：

- 左上：玩家 HP、鎧甲、回血計時／額度；
- 右上：城市 HP、城市受襲警示；
- 上方：A-B 關卡、剩餘飛機／下降／地面敵兵；
- 中央：與目前武器互斥的準心、狙擊鏡、普通炮鎖定框或多目標準心；
- 下方：五個武器槽、解鎖／冷卻、RPG 彈藥；
- 次要區域：金幣、r、A 與短錯誤提示。

白／紅／綠鎖定狀態必須同時有文字或形狀差異；錯誤提示在相同原因冷卻期間不逐幀重複堆疊。UI 尺寸依 Ursina UI 座標與視窗長寬比縮放，不能把 `0.21` 當固定螢幕百分比。

## 滑鼠契約

按鈕可點擊區必須等於視覺按鈕區；滑鼠與 `1..9,0` 商店快捷鍵都以同一 `UpgradeDefinition` ID 觸發。刪除與重生使用明確確認畫面，取消不發送 mutation event。
