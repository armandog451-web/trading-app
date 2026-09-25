# TradePulse - Lanzador Unificado
$ErrorActionPreference = "Stop"

$nodeDir = "C:\Users\edsel\AppData\Local\Microsoft\WinGet\Packages\OpenJS.NodeJS.LTS_Microsoft.Winget.Source_8wekyb3d8bbwe\node-v24.19.0-win-x64"
$pyDir = "C:\Users\edsel\AppData\Local\Programs\Python\Python311"
$pyScripts = "C:\Users\edsel\AppData\Local\Programs\Python\Python311\Scripts"

$env:Path = "$pyDir;$pyScripts;$nodeDir;" + $env:Path

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " TradePulse Quantitative Day Trading Engine" -ForegroundColor Green
Write-Host " Arquitectura Top-Down (Macro, COT, Opciones, Liquidez & R:R)" -ForegroundColor White
Write-Host "==========================================================" -ForegroundColor Cyan

$rootDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "Iniciando TradePulse Engine en http://localhost:8000..." -ForegroundColor Yellow

# Iniciar servidor backend unificado
$backendProc = Start-Process -FilePath "$pyDir\python.exe" -ArgumentList "run.py" -WorkingDirectory "$rootDir\backend" -PassThru

# Esperar 2 segundos a que el servidor inicialice
Start-Sleep -Seconds 2

# Abrir automáticamente el navegador web
Write-Host "Abriendo panel de control en tu navegador..." -ForegroundColor Green
Start-Process "http://localhost:8000"

Write-Host ""
Write-Host ">> APLICACION ACTIVA Y FUNCIONANDO <<" -ForegroundColor Green
Write-Host "URL Dashboard: http://localhost:8000" -ForegroundColor Cyan
Write-Host "Documentacion API: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "Para detener el servidor de trading, presiona Ctrl+C o cierra esta ventana." -ForegroundColor Gray

# Mantener el proceso activo hasta que el usuario cierre la ventana o presione Ctrl+C
try {
    Wait-Process -Id $backendProc.Id
} catch {
    Stop-Process -Id $backendProc.Id -Force -ErrorAction SilentlyContinue
}
