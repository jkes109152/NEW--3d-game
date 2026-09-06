# US6 戰役與重生驗收

公開 InputFrame 以免費 W01/W17/W03、無裝甲、無塔完成 A=2 全七關；控制器只輸入移動／瞄準／射擊，不修改敵血、跳勝利或補金幣。完整逐步事件見 [economy.json](economy.json)。

| 關卡 | 模擬秒數 | 防空發數 | 狙擊發數 | 結束玩家生命 | 獎勵 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1-1 | 9.592 | 1 | 6 | 100 | 125 |
| 1-2 | 18.667 | 2 | 12 | 100 | 135 |
| 2-1 | 18.308 | 4 | 6 | 100 | 150 |
| 2-2 | 30.700 | 4 | 18 | 100 | 160 |
| 2-3 | 54.133 | 4 | 40 | 80 | 170 |
| 2-4 | 55.308 | 9 | 27 | 100 | 330 |
| 2-5 | 63.600 | 14 | 19 | 100 | 490 |

總獎勵 1560，合法首次重生後 r=1、金幣 0、只剩三免費武器、無裝甲／塔／升級。新輪 1-1 保持起始敵人強度，9.592 秒通關、玩家生命 100、結算資產 187。全付費類別清除、歷史／設定保留另由 test_rebirth_v2 與 test_save_v2_matrix 覆蓋。

先前平衡失敗證據保留於 [首次測量](balance-before/economy.json)。依已授權的首版數值調整，先記錄 W17 傷害 2、W18 傷害 5、Boss 接近時間 60 秒再實作；不更改商品價格與獎勵。理由見 [數值表](../../specs/002-gameplay-expansion/balance.md) 及 [決策](../../specs/002-gameplay-expansion/decisions.md)。

test_difficulty_v2、test_campaign_v2、test_rebirth_v2、test_economy、test_campaign_progression、test_aircraft_rules 與 test_restart_persistence 覆蓋四成長公式、上限、A=19、獨立 FAST、失敗原關重試、重開 1-1、最終重打與舊輪操作隔離。見 [測試日誌](tests.log)。
