# Spec Kit（專案內安裝）

本專案使用 GitHub Spec Kit **1.0.4**，來源為官方 release `v1.0.4`，commit `cb610277fdea781fcfa83d20522c2db37c94068d`。

- CLI 與依賴：`.tools/spec-kit/`（獨立 Python 虛擬環境）
- 下載快取：`.tools/uv-cache/`
- Codex skills：`.agents/skills/speckit-*/`
- 模板、工作流程、專案原則與 PowerShell 腳本：`.specify/`

未安裝全域 specify 指令，也未修改全域 PATH。Python 與 uv 使用電腦上既有的安裝。`.tools/` 已加入 Git 忽略清單。

## 執行 CLI

在本專案目錄的 PowerShell 執行：

```powershell
.\specify.ps1 version
.\specify.ps1 --help
```

## SDD 工作流程

在此專案開啟新的 Codex 對話以載入專案 skills，依序使用：

1. `$speckit-constitution`：建立專案開發原則。
2. `$speckit-specify`：描述需求並建立規格。
3. `$speckit-plan`：建立實作計畫。
4. `$speckit-tasks`：分解工作。
5. `$speckit-implement`：執行實作。
6. `$speckit-converge`：檢查實作與規格是否一致。

另有 clarify、analyze、checklist 等 skills。專案憲章已完成產品化，目前為 1.4.0；新版規格與實作計畫位於 `specs/002-gameplay-expansion/`，001 保留為既有版本歷史。新功能先確認 `NNN-short-name` 工作分支及對應規格目錄，再依序執行 SDD；GitHub 操作一律使用 `gh` CLI，本機 Git 操作使用 `git`。規格或計畫完成不代表已完成實作或驗收。

## 重建本機工具環境

需要既有的 uv 與 Python 3.11 以上。在專案目錄執行：

```powershell
$env:UV_CACHE_DIR = Join-Path $PWD '.tools/uv-cache'
uv venv .tools/spec-kit --python 3.14
gh repo clone github/spec-kit .tools/spec-kit-source -- --branch v1.0.4 --depth 1
git -C .tools/spec-kit-source rev-parse HEAD
# 核對上列 SHA 等於文件指定版本，再從本機來源安裝。
uv pip install --python .tools/spec-kit/Scripts/python.exe .tools/spec-kit-source
.\specify.ps1 version
```

既有 `.specify/` 與 `.agents/skills/` 已初始化，不需再次執行 init。

官方文件：[GitHub Spec Kit](https://github.com/github/spec-kit)

002 改版採 Profile v2 獨立資料位置；開發與驗證方式見 [README](README.md)、[快速驗證](specs/002-gameplay-expansion/quickstart.md) 與 [驗收證據](artifacts/002-gameplay-expansion/acceptance.md)。所有執行證據保留於 `artifacts/002-gameplay-expansion/`，不將 001 基準當成新版通過。
