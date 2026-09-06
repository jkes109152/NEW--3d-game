# 啟動與回退驗證

日期：2026-09-06；分支：002-gameplay-expansion。Python 3.12.13、Windows x64，固定依賴沿用 requirements-game.txt。所有遊戲資料均使用隔離 root。

| 情境 | 命令／配置 | 實測 |
| --- | --- | --- |
| 中文及空白路徑 | `artifacts/launcher-copies/糖果 防線 中文/start_game.cmd --size 1280x720 --silent --offscreen --smoke-seconds 1 --screenshot ...` | 兩次退出 0 |
| 依賴準備後離線再啟動 | 上述兩次均設定 PIP_NO_INDEX=1，PIP_INDEX_URL 指向無服務的本機位址 | 使用已備妥的 .venv，沒有下載；兩次建立畫面 |
| 無音訊及低畫質 | `python tools/fallback_probe.py` | null 音訊、low、免費武器經公開 InputFrame 完成 1-1，125 金幣 |
| 缺可選圖樣 | 同一探測將可選紋理供應位置指向空目錄，經正常交易購買 W17 星星圖樣 | 基本材質回退，記錄缺少 textures/stars.png，程式未中止 |
| 啟動契約 | `tests.test_launcher_contract`，包含於完整測試 | 檢查入口、引數及錯誤退出碼；結果見 tests.log |

原始資料：[兩次啟動退出碼](launcher-results.json)、[第一次日誌](launcher-1.log)、[第二次日誌](launcher-2.log)、[回退紀錄](fallback/report.json)。畫面：[第一次](launcher-1.png)、[第二次](launcher-2.png)、[低畫質成功](fallback/low-silent-success.png)、[缺可選圖樣](fallback/missing-optional-pattern.png)。

啟動複本透過 junction 使用同一套已備妥的虛擬環境及素材；證明中文路徑及依賴準備後離線啟動，不代表全新電腦無 Python／無 wheel 也能離線安裝。null backend 是無聲回退驗證；未實際拔除使用者音訊硬體。原生流程另確認非 silent 音訊後端成功初始化、audio_error 為 null；沒有將未聆聽的音色主觀效果列為通過。
