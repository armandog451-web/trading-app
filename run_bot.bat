@echo off
rem -----------------------------------------------------------
rem Run AlgortimTrading‑robot bot
rem -----------------------------------------------------------
rem Change to script directory
cd /d "%~dp0"

rem Activate virtual environment
call env\Scripts\activate.bat
if errorlevel 1 (
    echo Failed to activate virtual environment
    pause
    exit /b 1
)

rem Run the bot
python bot.py

rem Keep window open after execution
pause
