# US3 射擊與投射物驗收

120 Hz、最多八個微步；有序命令保留短點擊，逐把 runtime 管理彈匣、射速餘量、上膛、點放、換彈與火箭配額。切槍取消換彈／未發點放而保留彈量與冷卻，暫停不推進任何有效時間。

18 種對地武器逐一實際命中、射空、扣彈、換彈、切槍及暫停，兩防空武器另驗單／多目標鎖定與發射快照。test_arsenal_matrix 的 0.3 秒長按發數為 W03～W20：1、3、1、3、3、1、2、4、4、5、3、2、1、1、1、1、1、1。數值直接摘錄定案表。見 [矩陣日誌](matrix.log) 與 [全測試](tests.log)。

test_weapon_timing、test_input_commands、test_hitscan_v2、test_rocket_collision、test_lock_and_missiles、test_multi_lock、test_pause_focus 覆蓋 30／60／144 Hz、0.06 秒時刻、八霰彈、射程 180 以上、首次掃掠碰撞、同距世界優先、表面爆炸可見性、到期無傷害、有限配額、固定導彈目標與失焦放開。

真實鍵盤 4 切 W06、左鍵扣彈 30→29、R 顯示 1.8 秒換彈、Esc 暫停／恢復已執行；見 [原生紀錄](native-input-shop-battle.json)。畫面效果與低畫質回收另由 [US7](us7.md) 驗證。
