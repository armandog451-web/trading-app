@echo off
REM Detención limpia para EXP-ST02 Autonomous Daemon
set SCRIPT_DIR=%~dp0
cd /d "C:\Users\edsel\Documents\trading-app-repo"
"C:\Users\edsel\Documents\trading-app-repo\.venv\Scripts\python.exe" "%SCRIPT_DIR%run_st02_service.py" --stop
