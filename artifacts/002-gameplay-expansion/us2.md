# US2 武器商店與自訂驗收

20 把武器、17 把付費商品、各自升級／配件／配色／圖樣與四類商店已接入十二交易框架。test_weapon_shop、test_weapon_customization、test_weapon_validation 與 test_arsenal_matrix 覆蓋每把傷害升級至五級、上限、缺錢、非法配件、重播及其餘 19 把完全不變；狙擊射程、AA 升級及配件收益／代價另有固定案例。見 [測試日誌](tests.log) 與 [全商品矩陣](matrix.log)。

原生操作使用隔離高餘額欄位，實際購買 W06（350）並升級傷害（200），從 100000 降至 99450；準備時放入第四槽，戰鬥數字鍵 4 確認 W06。購買沒有自動改出戰槽。原始資料見 [原生商店與戰鬥](native-input-shop-battle.json)。

所有商品的造型配方、能力與共用工廠識別由 catalog 情境及兩解析度 engine-probe 留存；引擎 API 情境與真實鍵鼠紀錄分別列示於 [US7](us7.md)。
