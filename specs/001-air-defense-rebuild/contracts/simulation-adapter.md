# 純規則模擬介面契約

引擎層不得直接修改規則物件的欄位；每個固定 tick 由適配器傳入不可變輸入快照，取回狀態快照與一次性事件。

## `InputFrame`

```text
move_x, move_z: -1..1
look_delta: {yaw: float, pitch: float}
jump_pressed: bool
fire_pressed: bool
aim_held: bool
weapon_slot: null | 1..5
pause_requested: bool
```

數字鍵只在解鎖槽位切換成功時改變 `weapon_slot`；非法槽位產生 `weapon_locked` 事件但不清除冷卻、彈藥或目前武器。E/G 不產生事件。

## `SimulationStepResult`

每個 `1/120` 秒 tick 回傳：

- `state_revision` 與 `attempt_id`；
- 玩家、城市、敵人、飛機、砲塔、導彈的只讀摘要（ID、位置、HP、phase、target_id）；
- HUD 狀態（武器、冷卻、彈藥、鎖定進度、錯誤提示）；
- 有序事件：`fired`、`hit`、`destroyed`、`drop_created`、`warning`、`damage`、`success`、`failure`、`operation_result`；
- 診斷計數（`active entities` 活動實體、`scheduled callbacks` 排程回呼、`dropped simulation steps` 丟棄的模擬步）。

事件按固定優先序與穩定 ID 排序，渲染層只能消費事件；事件含 `attempt_id`，不匹配目前當局時丟棄。

## 模擬介面邊界

- `scene.py` 將模型／碰撞器（collider）的實際位置與命中資訊映射成穩定 ID，將模擬快照呈現為 Entity 實體。
- `ui.py` 只派送 `InputFrame`、讀取 HUD 摘要與顯示事件，不自行計算傷害、金幣或進度。
- `audio.py` 只消費音效事件；缺少音效檔時使用無聲回退，不阻止 tick。
