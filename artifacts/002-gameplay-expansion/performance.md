# 效能與生命週期驗證

日期：2026-09-06；分支：002-gameplay-expansion。1280×720、中畫質，各暖機 10 秒後量測至少 60 秒。計時使用實際引擎繪製的 perf_counter 間隔與最後管線排空時間，保留逐幀原始秒數；P1 為 1/P99(frame_seconds)。

| 類型 | 飛機 | 量測秒數 | 幀數 | 平均 FPS | P1 FPS | 連續長幀 | 證據 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 原生視窗，最後造型修正前 | 4 | 60.006 | 6048 | 100.790 | 52.169 | 0 | [原始報告](performance-A4/A4-report.json) |
| 原生視窗，最後造型修正前 | 8 | 60.004 | 5232 | 87.194 | 45.530 | 0 | [原始報告](performance-A8/A8-report.json) |
| 最後版本離屏 GPU | 4 | 60.007 | 6382 | 106.355 | 72.469 | 0 | [原始報告](performance-current-A4/A4-report.json) |
| 最後版本離屏 GPU | 8 | 60.010 | 5674 | 94.550 | 67.853 | 0 | [原始報告](performance-current-A8/A8-report.json) |

A4 門檻為平均 55、P1 45 FPS、無連續兩幀各超過 250 ms；上列 A4 均通過。A8 依 SC-011 記錄 12 塔壓力與清理，不另把 A4 的 FPS 門檻加給 A8。最新命令與退出碼見 [量測執行紀錄](final-performance-checks.json)。原生數據與最後修改後離屏數據分列，沒有將最後版離屏測量冒充再次開啟原生視窗。

兩種情境均持續補充飛機、敵兵、玩家／城市生命與火箭配額，並實際發射 W12、W19、W20；負載驅動器不作通關證據。每秒保存活動飛機、敵兵、塔、導彈、火箭、核心曳光與額外效果；沒有單調持續累積。離開後活動彈體、效果、曳光與待處理輸入全部歸零，Entity=45、task=9、handler=1、UI layer=1、button=6。可重用池另列，沒有混作活動物件。

硬體：Intel Arc B580，OpenGL 4.6.0／驅動 32.0.101.6790；Windows 11 build 26200，處理器 Intel64 Family 6 Model 198 Stepping 2。Python 3.12.13；Cull/Draw、sync-video=false、繪製時鐘上限 120 FPS。完整原始字串見各報告 hardware。

兩解析度 engine_probe 各執行十輪準備／開始／暫停／結果／返回，十二個活動指標差異全為零；快取暖機後固定。見 [1280 十輪](1280x720/1280x720-engine-probe.json)、[1920 十輪](1920x1080/1920x1080-engine-probe.json)。expansion_probe 的 lifecycle 入口委派同一 engine_probe.run；此處採已執行的引擎入口證據，不另聲稱呼叫過 wrapper。

先前 performance-*diagnostic、performance、performance-final、screens 及二進位 profile 檔為調校／失敗過程，並非最後驗收；最後狀態只以上表、final-performance-checks.json 與兩個 engine-probe.json 為準。
