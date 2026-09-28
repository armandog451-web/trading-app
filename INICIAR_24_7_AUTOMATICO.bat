@echo off
title AlgortimTrading Robot - Monitor 24/7 (Watchdog Auto-Reinicio)
cd /d "%~dp0"

echo ============================================================
echo   AlgortimTrading Robot v2.0 PRO - Modo 24/7 Autonomo
echo ============================================================
echo Este monitor mantiene el robot activo de forma ininterrumpida.
echo Si el proceso se detiene o reinicia, se recuperara solo.
echo.

:LOOP
echo [%date% %time%] Iniciando servidor y motor de trading...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1"

echo.
echo [AVISO] El proceso se detuvo a las %time%.
echo Reiniciando en 5 segundos de forma automatica...
timeout /t 5 /nobreak >nul
goto LOOP
