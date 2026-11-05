@echo off
REM Lanzador en segundo plano para EXP-ST02 Autonomous Daemon
set SCRIPT_DIR=%~dp0
cd /d "C:\Users\edsel\Documents\trading-app-repo"
start "EXP-ST02-DAEMON" /min "C:\Users\edsel\Documents\trading-app-repo\.venv\Scripts\python.exe" "%SCRIPT_DIR%run_st02_service.py" --daemon
echo [EXP-ST02] Daemon iniciado en segundo plano.
