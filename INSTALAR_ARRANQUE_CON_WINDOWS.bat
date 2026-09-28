@echo off
title Instalar Arranque Automatico con Windows
cd /d "%~dp0"

echo ============================================================
echo   Configurando Arranque Automatico con Windows (24/7)
echo ============================================================
echo.

powershell -NoProfile -Command "$WshShell = New-Object -ComObject WScript.Shell; $startupPath = [Environment]::GetFolderPath('Startup'); $shortcut = $WshShell.CreateShortcut(Join-Path $startupPath 'AlgortimTrading_24_7.lnk'); $shortcut.TargetPath = '%~dp0INICIAR_24_7_AUTOMATICO.bat'; $shortcut.WorkingDirectory = '%~dp0'; $shortcut.Save(); Write-Host 'Configurado con exito en:' $startupPath"

echo.
echo [EXITO] Ahora el robot se iniciara solo cada vez que enciendas la PC o se reinicie.
echo.
pause
