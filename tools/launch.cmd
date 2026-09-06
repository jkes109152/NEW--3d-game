@echo off
setlocal
pushd "%~dp0.."
set "PYTHONUTF8=1"
if defined AIR_DEFENSE_PYTHON goto explicit
if exist ".venv\Scripts\python.exe" goto existing
py -3.12 -c "import sys; raise SystemExit(sys.version_info[:2] != (3,12))" >nul 2>&1
if not errorlevel 1 goto launcher
python -c "import sys; raise SystemExit(sys.version_info[:2] != (3,12))" >nul 2>&1
if not errorlevel 1 goto systempython
echo 找不到 Python 3.12.x。請安裝 64 位元 Python 3.12 後重試。
popd
exit /b 2
:explicit
"%AIR_DEFENSE_PYTHON%" "%~dp0bootstrap.py" %*
goto done
:existing
".venv\Scripts\python.exe" "%~dp0bootstrap.py" %*
goto done
:launcher
py -3.12 "%~dp0bootstrap.py" %*
goto done
:systempython
python "%~dp0bootstrap.py" %*
:done
set "result=%errorlevel%"
popd
exit /b %result%
