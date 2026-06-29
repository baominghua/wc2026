@echo off
setlocal
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File "%~dp0scripts\deploy-nas.ps1" -NasHost bmhlfc.top -NasUser admin -AppPort 12026
pause
