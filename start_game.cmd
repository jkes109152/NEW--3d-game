@echo off
setlocal
chcp 65001 >nul
call "%~dp0tools\launch.cmd" game %*
set "result=%errorlevel%"
if not "%result%"=="0" if not "%AIR_DEFENSE_NO_PAUSE%"=="1" pause
exit /b %result%
