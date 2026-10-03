@echo off
title AlgortimTrading Robot v2.0 PRO
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1"
if %errorlevel% neq 0 pause
