@echo off
title AI Trading Agent 1.0 — SuperRobot Core
cd /d "%~dp0"

set PYTHON_EXE=C:\Users\edsel\AppData\Local\Programs\Python\Python311\python.exe
if not exist "%PYTHON_EXE%" (
    if exist "%~dp0.venv\Scripts\python.exe" (
        set PYTHON_EXE=%~dp0.venv\Scripts\python.exe
    ) else (
        set PYTHON_EXE=python
    )
)

echo ==========================================================
echo  AI TRADING AGENT 1.0 -- SUPERROBOT
echo  Arquitectura Cuantitativa Modular y Determinista
echo  Modo Inicial: ANALYSIS_ONLY (Cero Riesgo Real)
echo ==========================================================
echo Iniciando Core Engine en http://localhost:8090...

rem Abrir navegador en segundo plano
start "" http://localhost:8090

rem Ejecutar servidor Uvicorn directamente en consola
"%PYTHON_EXE%" run_superrobot.py

if %errorlevel% neq 0 (
    echo.
    echo Ocurrio un error al ejecutar SuperRobot.
    pause
)
