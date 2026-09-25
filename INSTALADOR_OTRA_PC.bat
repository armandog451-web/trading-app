@echo off
title TradePulse - Instalador para Otra PC
cd /d "%~dp0"

echo ==============================================================
echo    TradePulse - Configurando en esta nueva PC
echo ==============================================================
echo.

echo 1. Verificando Python...
python --version
if %errorlevel% neq 0 (
    echo [ERROR] No se encontro Python instalado en esta computadora.
    echo Por favor descarga e instala Python 3.11 o superior desde python.org
    echo y asegurate de marcar 'Add Python to PATH'.
    pause
    exit /b 1
)

echo.
echo 2. Instalando librerias de Trading y Moomoo...
pip install -r backend\requirements.txt

echo.
echo ==============================================================
echo [EXITO] Configuracion completada con exito.
echo.
echo - Para abrir con Antigravity: Abre Antigravity y selecciona esta carpeta.
echo - Para iniciar el Bot 24/7: Ejecuta 'INICIAR_24_7_AUTOMATICO.bat'
echo - Para que inicie solo con Windows: Ejecuta 'INSTALAR_ARRANQUE_CON_WINDOWS.bat'
echo ==============================================================
echo.
pause
