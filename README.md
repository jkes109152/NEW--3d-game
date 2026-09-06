# 3D 防空守衛

Windows 單機第一人稱防空遊戲。鎖定來襲飛機，再處理空降敵兵，保護城市並升級裝備。

## 啟動

安裝 64 位元 Python 3.12.x 後，雙擊 `start_game.cmd`。首次會在專案 `.venv` 安裝固定依賴；後續可離線遊玩。路徑可含空白與繁體中文。離線首次安裝可將全部依賴的 wheel 套件放入 `tools/wheels/`。

## 操作

| 按鍵 | 功能 |
|---|---|
| WASD／滑鼠 | 移動／視角 |
| Space | 跳躍；主選單開始 |
| 左鍵／右鍵 | 攻擊／切換瞄準 |
| 1～5 | 防空炮、狙擊槍、手槍、RPG、多目標防空炮 |
| Esc／Enter | 暫停或返回／確認 |

E 與 G 沒有效果。每小關結束後手動開始下一關；重新載入存檔從 1-1 開始。失敗或完成最終關後，可花費金幣重生，保留永久升級。

## 存檔與測試

五欄位保存於 `%LOCALAPPDATA%/AirDefenseQuality/slot-1.json` 至 `slot-5.json`。損壞檔案需先備份再確認重建。測試一律注入隔離目錄。

雙擊 `run_tests.cmd` 執行語法檢查與規則測試。完整輸出與退出碼保留於 `artifacts/tests.log`。驗收結果見 `docs/ACCEPTANCE.md`。

啟動或依賴安裝失敗時查看 `artifacts/launcher-error.log`、`artifacts/dependency-install.log`；遊戲執行錯誤見 `artifacts/game-error.log`。沒有音訊裝置時使用無聲回退。
