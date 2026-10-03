@echo off
title TradePulse Trading Engine
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_tradepulse.ps1"
if %errorlevel% neq 0 pause
