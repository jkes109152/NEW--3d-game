# 完整驗證紀錄

日期：2026-09-06；開發分支：002-gameplay-expansion。Python 3.12.13、固定 requirements-game.txt，所有規則／引擎探測使用隔離存檔。交付前原始碼快照見 [SHA-256 清單](verified-source-sha256.json)，涵蓋 air_defense、tools、tests；Git 提交與遠端交付另列於 delivery.md。

| 已執行命令 | 結果 | 證據 |
| --- | --- | --- |
| `run_tests.cmd` | 退出 0，133 tests，OK | [日誌](tests.log)、[退出碼](final-checks.json) |
| `.venv/Scripts/python.exe -m compileall -q air_defense tests tools` | 退出 0 | [退出碼](final-checks.json) |
| `.venv/Scripts/python.exe -m pip check` | 退出 0，No broken requirements found | [退出碼](final-checks.json) |
| `python tools/engine_probe.py --size 1280x720 --output artifacts/002-gameplay-expansion/1280x720` | 退出 0，66 畫面、20 ID 一致、十輪清理差異 0 | [逐項輸出](1280x720/1280x720-engine-probe.json) |
| 同上，`--size 1920x1080` 與對應 output | 退出 0，同樣 66 畫面及十輪差異 0 | [逐項輸出](1920x1080/1920x1080-engine-probe.json) |
| `python tools/presentation_regression_probe.py --size 1280x720`／`1920x1080` | 各退出 0，每解析度 240 個預覽角度／包絡、六次畫質切換 | [1280](presentation-final/1280x720-report.json)、[1920](presentation-final/1920x1080-report.json) |
| `python tools/review_engine_probe.py` | 退出 0，三畫質、音量修改、十輪鎖定與清理 | [日誌](review-engine.log) |
| `python tools/fallback_probe.py` | 退出 0，無聲 low 完整 1-1、缺可選圖樣 | [報告](fallback/report.json) |
| `python tools/expansion_probe.py --scenario catalog --output artifacts/002-gameplay-expansion/catalog` | 退出 0，20／6／3 商品及兩解析度 ID 對照 | [報告](catalog/catalog.json) |
| `python tools/expansion_probe.py --scenario economy --output artifacts/002-gameplay-expansion` | 退出 0，免費七關 1560、重生後免費 1-1 | [完整合法輸入](economy.json) |
| `python tools/performance_probe.py --aircraft 4|8 --warmup 10 --duration 60 --offscreen --output ...` | 各退出 0；最後版真實 GPU 幀時間 | [性能紀錄](performance.md) |

引擎與性能工具的實際參數／退出碼另外保存於 [final-engine-checks.json](final-engine-checks.json) 與 [final-performance-checks.json](final-performance-checks.json)。133 個測試包含舊契約回歸、新版目錄、二十武器／六裝甲矩陣、時序、部署、投射物、十二交易保存故障及真實子程序崩潰邊界；純規則契約檢查未匯入圖形引擎。

日誌開頭出現的依賴安裝／修復失敗文字由 bootstrap 故障注入測試刻意產生；測試斷言及最終退出碼為 0，實際 pip check 無衝突。中文空白路徑與離線後續啟動見 [launcher.md](launcher.md)。

兩解析度各 11 張聯絡表已逐頁檢視，並查看 W01、W18、近距角色、低畫質成功、缺圖樣及啟動畫面的原尺寸圖片。中文行距、按鈕、價格資訊及模型位置修正後沒有再發現截斷或重疊。聯絡表依 engine-probe.json 的順序涵蓋全部 132 張畫面；原始 PNG 留在解析度目錄。

原生鍵鼠與未驗邊界見 [us7.md](us7.md)。使用者停止 Computer Use 後沒有再操作桌面；原生焦點切換、連續 WASD 長按及最後造型修正後的原生重跑未列為通過。這些紀錄不取代已執行的純規則／引擎回歸，也不把慢速輸入探測當性能或通關證據。

程式來源共 88 個 Python 檔案：[原始工作目錄 SHA-256](verified-source-sha256.json) 對應實測位元組；[LF 正規化 SHA-256](verified-source-sha256-lf.json) 用於核對 Git 依 .gitattributes 正規化換行後的內容，兩者只允許 CRLF／LF 差異。`diagnostics/`、`balance-before/` 及較早失敗探測為修復歷程，不列為最後通過結果。
