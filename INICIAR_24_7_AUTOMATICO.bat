@echo off
title TradePulse & Moomoo 24/7 Auto-Pilot
cd /d "%~dp0"

echo ==============================================================
echo    TradePulse & Moomoo 24/7 - Sistema de Auto-Recuperacion
echo    Objetivo: Mantener Bot y Moomoo siempre activos sin intervencion
echo ==============================================================
echo.

set "PY_EXE=%~dp0backend\.venv\Scripts\python.exe"
if not exist "%PY_EXE%" (
    set "PY_EXE=C:\Users\edsel\AppData\Local\Programs\Python\Python311\python.exe"
)
if not exist "%PY_EXE%" (
    set "PY_EXE=python.exe"
)

echo Iniciando Vigilante Centinela 24/7...
start "" "%PY_EXE%" "%~dp0backend\watchdog_24_7.py"

echo.
echo [OK] El sistema esta corriendo y auto-vigilado.
echo Si Moomoo o el Bot se caen, se reiniciaran solos en 10 segundos.
echo Puedes minimizar esta ventana.
timeout /t 5 >nul
