# AI TRADING AGENT 1.0 (SUPERROBOT) — LANZADOR UNIFICADO
$ErrorActionPreference = "Stop"

$rootDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Priorizar Python 3.11 del sistema o venv
$globalPy = "C:\Users\edsel\AppData\Local\Programs\Python\Python311\python.exe"
$venvPy = Join-Path $rootDir ".venv\Scripts\python.exe"

if (Test-Path $globalPy) {
    $pyExe = $globalPy
} elseif (Test-Path $venvPy) {
    $pyExe = $venvPy
} else {
    $pyExe = "python.exe"
}

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " AI TRADING AGENT 1.0 - SUPERROBOT" -ForegroundColor Green
Write-Host " Arquitectura Cuantitativa Modular y Determinista" -ForegroundColor White
Write-Host " Modo Inicial: ANALYSIS_ONLY (Cero Riesgo Real)" -ForegroundColor Yellow
Write-Host "==========================================================" -ForegroundColor Cyan

Write-Host "Iniciando Core Engine en http://localhost:8090..." -ForegroundColor Yellow

# Iniciar servidor backend de SuperRobot
$backendProc = Start-Process -FilePath $pyExe -ArgumentList "run_superrobot.py" -WorkingDirectory $rootDir -PassThru

# Esperar 2.5 segundos para arranque del servidor
Start-Sleep -Seconds 2.5

# Abrir en Google Chrome o navegador predeterminado
Write-Host "Abriendo panel de control institucional..." -ForegroundColor Green
$chromePaths = @(
    "C:\Program Files\Google\Chrome\Application\chrome.exe",
    "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe"
)
$chromeExe = $null
foreach ($cp in $chromePaths) {
    if (Test-Path $cp) {
        $chromeExe = $cp
        break
    }
}

if ($chromeExe) {
    Start-Process -FilePath $chromeExe -ArgumentList "http://localhost:8090"
} else {
    Start-Process "http://localhost:8090"
}

Write-Host ""
Write-Host "SUPERROBOT ACTIVO Y OPERANDO" -ForegroundColor Green
Write-Host "URL Dashboard: http://localhost:8090" -ForegroundColor Cyan
Write-Host "Documentacion API (Swagger): http://localhost:8090/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "Para detener el servidor, presiona Ctrl+C o cierra esta ventana." -ForegroundColor Gray

try {
    Wait-Process -Id $backendProc.Id
} catch {
    Stop-Process -Id $backendProc.Id -Force -ErrorAction SilentlyContinue
}
