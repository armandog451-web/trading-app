@echo off
title Sincronizar Cambios con GitHub
cd /d "%~dp0"
set "PATH=%LOCALAPPDATA%\Programs\Git\cmd;%PATH%"

echo ==============================================================
echo    TradePulse - Guardando y Sincronizando con GitHub
echo ==============================================================
echo.

git status --short
echo.
echo Preparando cambios...
git add .
git commit -m "Actualizacion automatica: %date% %time%"
echo.
echo Subiendo cambios a GitHub (repositorio armandog451-web/trading-app)...
git push origin main

if %errorlevel% equ 0 (
    echo.
    echo ==============================================================
    echo [EXITO] Todos los cambios se guardaron y subieron a GitHub.
    echo ==============================================================
) else (
    echo.
    echo [AVISO] Si es la primera vez que subes desde esta PC, inicia sesion en la ventana que aparece.
)
echo.
pause
