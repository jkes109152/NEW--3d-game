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

另有 clarify、analyze、checklist 等 skills。專案原則目前仍是官方模板，尚未填入產品需求。

## 重建本機工具環境

需要既有的 uv 與 Python 3.11 以上。在專案目錄執行：

```powershell
$env:UV_CACHE_DIR = Join-Path $PWD '.tools/uv-cache'
uv venv .tools/spec-kit --python 3.14
uv pip install --python .tools/spec-kit/Scripts/python.exe 'specify-cli @ git+https://github.com/github/spec-kit.git@cb610277fdea781fcfa83d20522c2db37c94068d'
.\specify.ps1 version
```

既有 `.specify/` 與 `.agents/skills/` 已初始化，不需再次執行 init。

官方文件：https://github.com/github/spec-kit
