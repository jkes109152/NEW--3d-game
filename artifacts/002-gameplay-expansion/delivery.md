# 002 改版交付紀錄

[PR #2：完成糖果防線：裝備自訂、鳥瞰部署與重生成長](https://github.com/jkes109152/NEW--3d-game/pull/2) 已於 2026-09-06 22:34:36（Asia/Taipei）合併至 `main`。原功能分支 `002-gameplay-expansion` 的本機、遠端及追蹤參照已安全清除。

| 項目 | 已確認結果 |
| --- | --- |
| 倉庫／執行帳戶 | jkes109152/NEW--3d-game／jkes109152；gh 查詢權限為 ADMIN |
| 功能提交 | `3267a27c63b4afdb12c44baaeb29502fa7a1e26c`，445 個檔案；88 個 Python 來源與驗證的 LF 雜湊一致 |
| PR 目標／狀態 | main／MERGED；不是以 CLOSED 狀態推定合併 |
| 合併提交 | `6b6a59e3fcd58215bd55343616c4b668125da0f5` |
| 合併前狀態 | MERGEABLE／CLEAN；headRefOid 與受驗功能提交完全一致 |
| 必要檢查／審查 | main 未受保護、適用規則為空；PR checks／reviews 均無項目。沒有宣稱遠端 CI 或人工批准通過 |
| 本機驗證 | 133 項測試、編譯、依賴、矩陣、兩解析度畫面與清理、免費通關及性能實測，見 [驗收追蹤](acceptance.md) |
| 同步／納入證據 | gh repo sync 快轉本機 main；本機 HEAD 與遠端 main 同為合併提交，功能提交是 main 的祖先 |
| 清理前保護 | 工作目錄乾淨，僅此一工作樹；遠端功能分支仍為功能提交，沒有新增未合併提交 |
| 清理後結果 | gh branches 僅有 main；本機 branch 僅有 main；失效 origin/002-gameplay-expansion 參照已刪除 |

合併前的結構化結果及退出碼見 [PR 關卡](pr-2-preflight.json)；合併結果見 [gh PR JSON](pr-2.json)；清理後遠端清單見 [分支 JSON](remote-branches-after-pr-2.json)，另有 [本機再次核對](local-cleanup-after-pr-2.json)。`gh pr checks` 在沒有檢查時退出碼為 1，輸出為「no checks reported」；此結果與空 statusCheckRollup、無適用分支規則一致，沒有略過失敗或待執行的檢查。

## 實際操作

下列遠端查詢／變更全部透過 gh。首次 pr create 因 Git 擁有者檢查停止，未寫入遠端；後續只在該命令的程序環境追加本專案 safe.directory，未修改使用者全域設定。gh 原生建立 PR 的選單將分支上傳至既有 origin，未使用直接 git push。

```powershell
gh api user --jq .login
gh repo view jkes109152/NEW--3d-game --json nameWithOwner,defaultBranchRef,url,viewerPermission
gh api repos/jkes109152/NEW--3d-game/rules/branches/main
gh pr create --repo jkes109152/NEW--3d-game --base main --title '完成糖果防線：裝備自訂、鳥瞰部署與重生成長' --body-file artifacts/002-gameplay-expansion/pr-body.md
gh pr checks 2 --repo jkes109152/NEW--3d-game --json name,state,bucket,workflow,link
gh pr merge 2 --repo jkes109152/NEW--3d-game --merge --match-head-commit 3267a27c63b4afdb12c44baaeb29502fa7a1e26c
gh pr view 2 --repo jkes109152/NEW--3d-game --json url,state,mergedAt,mergedBy,mergeCommit,baseRefName,headRefName,headRefOid
gh repo sync --branch main --source jkes109152/NEW--3d-game
gh api --method DELETE repos/jkes109152/NEW--3d-game/git/refs/heads/002-gameplay-expansion
gh api repos/jkes109152/NEW--3d-game/branches --paginate
```

本機只用 git 進行 status／diff／add／commit／switch／merge-base／branch／update-ref。未直接推送 main；未呼叫 GitHub 瀏覽器、連接器或其他 HTTP 工具。無分支保護規則需要例外放行，合併未使用 `--admin`。

## 紀錄收尾與驗證限制

T094–T097 的勾選及本頁在上述結果全部確認後才更新。為保留 PR 流程，文件收尾使用相同功能編號的 `002-delivery-record` 分支另送 PR，未直接提交到 main；該文件 PR 不改遊戲來源，原始 88 檔的 LF 雜湊持續可核對。

原生失焦／恢復、連續 WASD 長按、主觀音色及最後造型修正後的原生重跑仍未驗證；使用者停止 Computer Use 後未再呼叫該工具。其餘原生、離屏與純規則證據按類別分列，詳見 [US7](us7.md) 與 [性能](performance.md)。此限制未被合併或任務勾選掩蓋。
