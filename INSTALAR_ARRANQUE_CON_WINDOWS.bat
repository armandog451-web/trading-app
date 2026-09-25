@echo off
title Instalar Auto-Arranque de TradePulse y Moomoo
cd /d "%~dp0"

echo ==============================================================
echo    Instalador de Auto-Arranque 24/7 con Windows
echo ==============================================================
echo.
echo Creando Tarea Programada en Windows para que TradePulse y Moomoo
echo arranquen automaticamente cada vez que se encienda la computadora...
echo.

schtasks /create /tn "TradePulse_24_7_AutoPilot" /tr "\"%~dp0INICIAR_24_7_AUTOMATICO.bat\"" /sc onlogon /rl highest /f

if %errorlevel% equ 0 (
    echo.
    echo ==============================================================
    echo [EXITO] Tarea registrada correctamente en Windows.
    echo A partir de ahora, Moomoo y el Bot arrancaran automaticamente
    echo cada vez que inicies Windows, sin que tengas que hacer nada.
    echo ==============================================================
) else (
    echo.
    echo [AVISO] Si dio error de permisos, por favor haz clic derecho
    echo sobre este archivo y selecciona 'Ejecutar como Administrador'.
)

echo.
pause
