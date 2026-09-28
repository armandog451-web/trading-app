@echo off
title Instalador AlgortimTrading Robot - Otra PC 24/7
cd /d "%~dp0"

echo ============================================================
echo   Instalador Automatizado para Nueva PC (24/7)
echo ============================================================
echo.

echo 1. Verificando Python...
python --version
if errorlevel 1 (
    echo [ERROR] Python no esta instalado o no esta en el PATH.
    echo Por favor instala Python 3.11 desde https://www.python.org/downloads/
    echo Asegurate de marcar la casilla "Add Python to PATH" durante la instalacion.
    pause
    exit /b 1
)

echo.
echo 2. Instalando dependencias de trading y librerias...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Fallo al instalar las dependencias de requirements.txt.
    pause
    exit /b 1
)

echo.
echo 3. Configurando variables de entorno...
if not exist ".env" (
    copy .env.example .env
    echo Se ha creado el archivo .env con valores predeterminados.
)

echo.
echo 4. Creando Acceso Directo en el Escritorio...
powershell -NoProfile -ExecutionPolicy Bypass -File "create_desktop_shortcut.ps1"

echo.
echo ============================================================
echo   INSTALACION COMPLETADA CON EXITO
echo ============================================================
echo Para iniciar el robot:
echo   - Haz doble clic en el acceso directo de tu Escritorio
echo   - O ejecuta "start.bat"
echo.
echo Para que arranque solo cuando enciendas la PC:
echo   - Ejecuta "INSTALAR_ARRANQUE_CON_WINDOWS.bat"
echo ============================================================
pause
