# 快速驗證指南：002 改版

**狀態**：新版功能與下列工具已實作。實際通過、未驗項與交付狀態以 [驗收入口](../../artifacts/002-gameplay-expansion/acceptance.md) 及 [任務](tasks.md) 為準；001 證據保留為歷史紀錄。

## 環境與基準

使用 Windows x64、專案 Python 3.12.x `.venv` 及 requirements-game.txt 固定依賴。正式使用者仍可雙擊 start_game.cmd；首次離線安裝須備齊 tools/wheels，之後可離線遊玩。

```powershell
Set-Location 'C:\Users\lamuness\Desktop\game'
git branch --show-current
& .\.venv\Scripts\python.exe --version
& .\.venv\Scripts\python.exe -m pip check
& .\.specify\scripts\powershell\check-prerequisites.ps1 -Json -PathsOnly
```

開發時分支與 FEATURE_DIR 應對應 002-gameplay-expansion；交付完成後依憲章切回 main。環境為 Python 3.12.13，依賴檢查與最新測試結果見 [驗證紀錄](../../artifacts/002-gameplay-expansion/verification.md)。[研究](research.md) 中的 82 項為實作前基準。

## 實作後的隔離啟動與規則測試

test_runner 及工具均使用隔離的 v2 根目錄；正式遊戲資料的位置與驗證規則見 [保存契約](contracts/save-transactions.md)。手動驗證後還原原有環境設定：

```powershell
$validationRoot = Join-Path ([System.IO.Path]::GetTempPath()) ('air-defense-v2-' + [guid]::NewGuid().ToString('N'))
$previousSaveRoot = $env:AIR_DEFENSE_V2_SAVE_DIR
try {
    $env:AIR_DEFENSE_V2_SAVE_DIR = $validationRoot
    & .\run_tests.cmd
    & .\.venv\Scripts\python.exe -m air_defense.main --size 1280x720 --silent
} finally {
    $env:AIR_DEFENSE_V2_SAVE_DIR = $previousSaveRoot
}
```

預期 run_tests.cmd 回 0，artifacts/tests.log 保存真實測試退出碼；遊戲建立新版五欄位，舊版根目錄完全不變。保留測試根目錄及日誌供檢查，勿把臨時根目錄路徑設定留給正式遊玩。

## V01～V02：起始、商店、自訂與配置

1. 選一個空欄位，新檔零金幣、W01/W17/W03；2 分鐘內經三步準備開始 1-1，無裝甲／無塔可用。
2. 取消準備後金幣／庫存不變；返回前一步草稿保留。嘗試重複武器、未擁有武器、沒有空戰／地面用途，均不能出戰；空兩槽合法。
3. 使用專用有足夠金幣的測試資料，逐頁確認 20 武器、6 裝甲、3 砲塔數量，商店沒有裝備／Game Pass 按鈕。
4. 只升級、自訂 W17，確認 W18 和其餘武器不變；比較下級傷害、射程、價格與配件收益／代價，重選已購外觀不扣款。
5. 更改五槽順序，進戰鬥確認種類／準心／聲音跟隨武器 ID；不是槽 2 才能開狙擊鏡。

## V03～V04：射擊、時間與投射物

- 對全部武器各測單擊、長按、鬆開、射空、R、切槍、暫停及失焦；具體預期見 [戰鬥契約](contracts/combat-simulation.md)。
- 比較 30／60／144 Hz、相同有效模擬時間的全自動發數；0.06 秒間隔不得逐發捨入而變慢。短於一步的 down/up 與換彈事件不得吞掉或重複。
- 半自動長按只射一發；三連發剩兩發只射兩發；全自動空匣自動換彈後可續射，切槍取消換彈但不能補彈。
- 霰彈八顆可以各中同一敵人；狙擊有效射程超過 180 可實際命中；牆後、射程外不能受傷，射空仍耗彈。
- W19/W20 各自只有每關 3／5 發，飛行中尚未命中不扣敵血；測薄牆高速掃掠、地面、敵人、表面遮擋、半徑端點與到期無爆炸。
- W01/W02 導彈在切槍後仍使用發射傷害；多目標目標死亡不改追；暫停後所有彈體／換彈／點放凍結並需新的按下才恢復射擊。

## V05～V06：裝甲與部署

保持自身等級相同，逐件穿六裝甲量測生命、速度、減傷、回血等待／速度／預算；測不穿與更換不疊加，城市傷害不因玩家裝甲下降。

以 r=0、1、2、4、6 的隔離資料檢查容量 0、2、4、8、12；r=0 只能預覽。逐台購買同型塔，確認不同 ID、跨關保留、不超量且同台不能重複放置。

鳥瞰實際點擊地面、移動、移除、平移／縮放，確認側欄點擊不放塔。測塔距 3 合法、少 0.01 不合法，地圖內縮、出生區及通道、障礙物相切不合法；射程預覽與實際選敵共用邏輯，防空高度限制有說明。T03 要持續可見一秒；混合對地塔不得打穿奇數最大生命 Boss 的精確半血。

## V07～V08：戰役、重生與保存

- 免費三武器、無裝甲、無塔合法完成 A=2 七關，獎勵依序 125、135、150、160、170、330、490，總計 1560；不能用直接改血或加錢的探測當可玩性證據。
- 在較後關卡分別觸發城市、撞城、玩家敗北；結算保存後顯示下一次出擊 1-1，返回主選單的「開始防守 1-1」及實際建立的當局一致，金幣／裝備保留。注入保存失敗時不得提前出戰，重試後仍從 1-1 開始。
- 勝利按鈕顯示「前往下一關（實際關卡）」；測 1-1→1-2、1-2→2-1、重生一次的 2-3→3-1 及最終 3-7→1-1，點擊後進入裝甲準備，確認配置保存後才建立該關。Esc 仍能回主選單；舊按鈕連點不跳過準備或重發獎勵。
- 重啟由 1-1 開始；最終成功可以同規模重打累積金幣，重生資格保留。
- 裝滿各類商品後確認重生，金幣及所有付費成果清空，重新配發三基礎武器，歷史與設定保留；新輪 1-1 的敵人強度仍為基準，並以重新配發的三武器、無裝甲及無塔實際完成該關，保存合法輸入與結算證據。
- 五欄位混合購買／自訂／部署後重開，各自還原；對十二種業務交易分別注入保存失敗，確認完整候選、原檔、阻擋操作與重試結果。
- 比較模擬舊版欄位前後位元組、位置及修改時間；測版本 1／99、損壞、重複 key、NaN、備份失敗、取消刪除及舊輪延遲請求。

## V09～V10：畫面、效果、性能與交付

以下工具可直接執行；engine_probe 預設為離屏，performance_probe 預設建立原生視窗。各工具的隔離配置、合法輸入及負載補給方式會標示於輸出。

```powershell
& .\.venv\Scripts\python.exe tools\engine_probe.py --scenario expansion --size 1280x720 --output artifacts\002-gameplay-expansion\1280x720
& .\.venv\Scripts\python.exe tools\engine_probe.py --scenario expansion --size 1920x1080 --output artifacts\002-gameplay-expansion\1920x1080
& .\.venv\Scripts\python.exe tools\expansion_probe.py --scenario catalog --output artifacts\002-gameplay-expansion\catalog
& .\.venv\Scripts\python.exe tools\expansion_probe.py --scenario economy --output artifacts\002-gameplay-expansion\economy
& .\.venv\Scripts\python.exe tools\expansion_probe.py --scenario lifecycle --output artifacts\002-gameplay-expansion\lifecycle
& .\.venv\Scripts\python.exe tools\performance_probe.py --aircraft 4 --warmup 10 --duration 60 --output artifacts\002-gameplay-expansion\performance-A4
& .\.venv\Scripts\python.exe tools\performance_probe.py --aircraft 8 --warmup 10 --duration 60 --output artifacts\002-gameplay-expansion\performance-A8
```

每個解析度保留選檔、主選單、四分類、武器自訂、三步準備／最終確認、戰鬥、暫停及結果截圖；catalog 另保留二十武器各兩項差異、六裝甲與三塔證據。用實際滑鼠／鍵盤再走完整流程並另列記錄，自動 probe 不代替真實輸入。

`tools/presentation_regression_probe.py --size 1280x720|1920x1080` 另檢查二十武器最大預覽倍率的十二個角度、合併後球體模板與六次畫質切換。`tools/review_engine_probe.py` 檢查既有材質與十輪清理；`tools/fallback_probe.py` 驗低畫質、無聲完整 1-1 及缺少可選圖樣。`performance_probe.py --offscreen` 可量測離屏 GPU 幀時間，報告會明列種類，不得稱為原生視窗或鍵鼠驗證。

2026-09-07 結算修訂可執行 `tools/result_navigation_probe.py --size 1280x720 --output artifacts/002-gameplay-expansion/result-navigation/1280x720`，再以 `--size 1920x1080` 及對應輸出目錄重跑另一解析度。工具驗敗北 3-1→1-1、四種勝利下一關、實際按鈕／Enter／Esc、過期按鈕與當局關卡，僅使用隔離檔案及離屏引擎入口。最新證據見 [結算導覽驗收](../../artifacts/002-gameplay-expansion/result-navigation/acceptance.md)。

預期 A4 平均≥55 FPS、P1≥45 FPS、無連續兩幀各超過 250 ms；A8 十二塔加全自動／火箭負載量測足 60 秒，記錄硬體、原始幀時間及每秒物件數，結束回基準。十輪無持續新增 Entity／task／input handler／彈體／UI；快取單列。

以含繁體中文及空白的測試路徑檢查啟動、離線後續啟動、無音訊與低畫質；無原生視窗／輸入能力時明列未驗證。所有工具必須傳回真實退出碼，最後以 `$speckit-converge` 對照需求並將尚未完成者交回任務，不可只憑產出檔案宣稱交付。
