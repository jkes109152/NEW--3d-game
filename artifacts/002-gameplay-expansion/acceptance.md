# 002 改版驗收與需求追蹤

日期：2026-09-06；規格：[糖果風防空守衛](../../specs/002-gameplay-expansion/spec.md)；開發分支：002-gameplay-expansion。實作及下列驗證已完成；[PR #2](https://github.com/jkes109152/NEW--3d-game/pull/2) 已合併至 main，兩端功能分支已清理，實際結果見 [交付紀錄](delivery.md)。

2026-09-06 基準的 133 項測試、兩解析度各 66 畫面、二十武器／六裝甲／十二交易矩陣、免費七關及重生後首局、十輪清理與 A4／A8 繪製量測均有實際輸出。[原始命令與退出碼](verification.md) 列出當時測試及資料；[來源雜湊](verified-source-sha256.json) 對應該次基準，保留原檔。

2026-09-07 結算導覽修訂改為敗北下一局回 1-1、勝利主按鈕直接進入實際下一關準備。最新 137 項測試、兩解析度結算導覽及來源雜湊另見 [修訂驗收](result-navigation/acceptance.md)；以下 FR-024 的新行為以該紀錄為準，歷史原關重試證據不再用作目前行為依據。

## 功能需求

「通過」只指本列所列證據涵蓋的行為，不代表額外未執行的人工驗證。原生焦點切換、連續 WASD 長按、音色主觀聆聽與最後造型修正後的原生重跑未完成，詳見 [原生證據範圍](us7.md)。

| 需求 | 實作／行為 | 實際證據 | 結果 |
| --- | --- | --- | --- |
| FR-001 | Windows 離線、五欄位、第一人稱及手動逐關 | [首局](us1.md)、[啟動](launcher.md)、test_campaign_integration | 通過 |
| FR-002 | v2 獨立五欄位、零資產及三免費武器 | [基礎](foundation.md)、test_save_v2_matrix | 通過 |
| FR-003 | 裝甲→五槽→鳥瞰→確認；可返回及取消 | [首局](us1.md)、test_preparation_flow、兩解析度畫面 | 通過 |
| FR-004 | 已擁有不重複五槽、空槽及空地用途驗證 | test_armor_loadout、test_preparation、[原生切槍](us7.md) | 通過 |
| FR-005 | 四商店、購買不裝備、僅遊戲金幣 | [商品](us2.md)、[畫面](us7.md)、test_weapon_shop | 通過 |
| FR-006 | 20 武器、3 免費、17 金幣商品 | [目錄](catalog/catalog.json)、test_catalog、test_arsenal_matrix | 通過 |
| FR-007 | 各武器獨立能力與升級上限 | [商品](us2.md)、test_arsenal_matrix | 通過 |
| FR-008 | 相容配件、外觀所有權與重選不扣款 | test_weapon_customization、test_arsenal_matrix、[商品](us2.md) | 通過 |
| FR-009 | 基礎／有效／下級數值、價格、上限及前置 | [商品](us2.md)、[目錄](catalog/catalog.json)、自訂畫面 | 通過 |
| FR-010 | 半自動、全自動、點放及手動上膛 | [戰鬥](us3.md)、test_weapon_timing、test_arsenal_matrix | 通過 |
| FR-011 | 彈匣、R／自動換彈、火箭配額與防空冷卻 | [戰鬥](us3.md)、test_weapon_timing、原生 R 紀錄 | 通過 |
| FR-012 | 射空扣彈、射程、掩體及八顆獨立霰彈 | test_hitscan_v2、test_weapon_validation、[戰鬥](us3.md) | 通過 |
| FR-013 | 可見彈體、首次碰撞爆炸、有限配額 | test_rocket_collision、test_lock_and_missiles、[戰鬥](us3.md) | 通過 |
| FR-014 | 爆炸半徑／遮擋／目標類型與同敵一次傷害 | test_rocket_collision、[戰鬥](us3.md) | 通過 |
| FR-015 | 20 武器彈藥效果、核心曳光、命中及回收 | [畫面](us7.md)、[壓力及清理](performance.md)、test_audio_assets | 通過 |
| FR-016 | 切槍保留資源、暫停／失焦凍結及恢復重按 | test_pause_focus、test_weapon_timing、[原生暫停](us7.md) | 規則及暫停通過；原生失焦未驗 |
| FR-017 | 六裝甲固定定位、最多一件且可不穿 | [裝甲矩陣](us4.md)、test_armor_matrix | 通過 |
| FR-018 | 血量／回血額度、正傷害下限及城市隔離 | [裝甲矩陣](us4.md)、test_armor_combat | 通過 |
| FR-019 | 三類逐台塔、跨關庫存、首次重生開放 | [砲塔](us5.md)、test_turret_inventory | 通過 |
| FR-020 | 2r 容量、庫存分離、12 台無舊上限 | test_deployment、[A8 十二塔](performance.md) | 通過 |
| FR-021 | 鳥瞰互動、合法位置、遮擋及目標射程預覽 | [砲塔](us5.md)、[原生部署](us7.md)、引擎投影斷言 | 通過 |
| FR-022 | 三塔選敵／鎖定／冷卻及 Boss 精確半血 | test_turret_targeting、[砲塔](us5.md) | 通過 |
| FR-023 | 關卡生命／速度／轉彎成長及上限 | test_difficulty_v2、test_aircraft_rules、[戰役](us6.md) | 通過 |
| FR-024 | 七關順序／獎勵、敗北回 1-1、勝利前往下一關準備、重生資格與費用 | [結算修訂](result-navigation/acceptance.md)、test_result_navigation、test_campaign_v2；[原戰役](us6.md) 保留未取代的順序／獎勵證據 | 通過 |
| FR-025 | 重生清楚確認、全部清空、免費重發及 1-1 | test_rebirth_v2、[戰役](us6.md)、重生確認畫面 | 通過 |
| FR-026 | 全付費成果清除、歷史／設定保留、拒絕舊輪重送 | test_rebirth_v2、test_transaction_v2、[戰役](us6.md) | 通過 |
| FR-027 | 免費通關與可累積足夠重生金幣 | [完整合法輸入](economy.json)、[戰役](us6.md) | 通過 |
| FR-028 | 保存所有擁有成果及配置，重啟 1-1 | test_profile_v2、test_restart_persistence、[保存矩陣](us7.md) | 通過 |
| FR-029 | 十二交易指紋去重、完整候選及相同成果重試 | test_transaction_v2、test_save_v2_matrix、[基礎](foundation.md) | 通過 |
| FR-030 | 嚴格 JSON、原子替換、備份、確認刪除及欄位隔離 | test_save_recovery、test_save_v2_matrix、[保存矩陣](us7.md) | 通過 |
| FR-031 | 全介面、人物、武器、飛機、砲塔及城市糖果造型 | [132 畫面及修正](us7.md)、[授權](../../assets/LICENSES.md) | 通過 |
| FR-032 | 20 武器部件差異、裝甲輪廓、五槽及彈藥 HUD | [目錄](catalog/catalog.json)、[畫面](us7.md) | 通過 |
| FR-033 | 兩解析度繁中、鍵鼠及既有設定 | [畫面／原生流程](us7.md)、test_settings、畫質回歸 | 通過；原生長按邊界未驗 |
| FR-034 | 中文路徑、離線、null 音訊、缺可選資產及 low | [啟動](launcher.md)、[效能](performance.md)、[驗證](verification.md) | 通過；證據種類明列 |

## 成功標準

| 標準 | 量測結果／來源 | 結果 |
| --- | --- | --- |
| SC-001 | 空欄位以 W01/W17/W03、無裝甲零塔，選檔至開戰 92.593 秒；[原生首局](us1.md) | 通過 |
| SC-002 | 20 武器、6 裝甲、3 塔逐項數值及輪廓；[目錄](catalog/catalog.json)、[矩陣](matrix.log) | 通過 |
| SC-003 | 每把升級／自訂後其餘 19 把不變，滿級、缺錢、非法配件及重送；test_arsenal_matrix | 通過 |
| SC-004 | 18 對地＋2 防空全矩陣，30／60／144 Hz 及一個微步邊界；[戰鬥](us3.md) | 通過 |
| SC-005 | 敵人、地面、薄牆、半徑端點、遮擋、到期與一次傷害；test_rocket_collision | 通過 |
| SC-006 | 六裝甲的移動／跳躍／傷害／回血及城市隔離；[裝甲](us4.md)、test_armor_matrix | 通過 |
| SC-007 | r=0/1/2/4/6 容量 0/2/4/8/12、幾何及預覽／攻擊共用查詢；[砲塔](us5.md) | 通過 |
| SC-008 | 免費七關獎勵 1560、全付費清除、下一輪免費 1-1；[合法通關](economy.json)、[戰役](us6.md) | 通過 |
| SC-009 | 五欄位、舊檔位元組／位置／mtime、十二交易故障與原子替換前後真實程序退出；[保存](us7.md) | 通過 |
| SC-010 | 兩解析度各 66 畫面全數檢視；原生滑鼠完成準備／商店／部署／結果流程；[呈現](us7.md) | 通過，原生與離屏範圍分列 |
| SC-011 | A4 原生平均 100.790／P1 52.169；最後版離屏 106.355／72.469；A8 十二塔最後版離屏 94.550／67.853，清理歸零；[性能](performance.md) | 通過，最後版本未重跑原生視窗 |
| SC-012 | 兩解析度各十輪活動物件差異 0；null 音訊＋low 以合法輸入通過 1-1；[清理](performance.md)、[回退](launcher.md) | 通過 |

## 收斂與交付

功能、規則及呈現的已發現缺陷均修正並重驗。speckit-converge 已核對 34 FR、12 SC、35 個故事驗收情境、11 個邊界情況、9 組技術決策及 8 項憲章原則。第一輪發現交付證據未齊（F1，T097）及 SDD 階段狀態過時（F2，T098），依技能只追加第 11 階段，返回 implement 後完成文件修訂與 gh 交付。原交付的 98 項任務按當時實際結果勾選；2026-09-07 的 T099–T102 另見修訂驗收，詳見 [收斂紀錄](convergence.md) 及 [交付紀錄](delivery.md)。原生未驗範圍仍維持明確標示。
