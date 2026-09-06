@echo off
setlocal
chcp 65001 >nul
call "%~dp0tools\launch.cmd" test %*
exit /b %errorlevel%
