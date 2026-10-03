# AlgortimTrading Robot v2.0 PRO - Lanzador Unificado
$ErrorActionPreference = "Stop"

$rootDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Priorizar el entorno virtual .venv del proyecto o Python global
$venvPy = Join-Path $rootDir ".venv\Scripts\python.exe"
$globalPy = "C:\Users\edsel\AppData\Local\Programs\Python\Python311\python.exe"

if (Test-Path $venvPy) {
    $pyExe = $venvPy
} elseif (Test-Path $globalPy) {
    $pyExe = $globalPy
} else {
    $pyExe = "python.exe"
}

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " AlgortimTrading Robot v2.0 PRO" -ForegroundColor Green
Write-Host " Motor Cuantitativo Hibrido (Moomoo & Alpaca + Telegram)" -ForegroundColor White
Write-Host "==========================================================" -ForegroundColor Cyan

Write-Host "Iniciando AlgortimTrading Robot en http://localhost:8050..." -ForegroundColor Yellow

# Iniciar servidor FastAPI de AlgortimTrading Robot (server.py)
$robotProc = Start-Process -FilePath $pyExe -ArgumentList "server.py" -WorkingDirectory $rootDir -PassThru

# Esperar 2.5 segundos para arranque del servidor
Start-Sleep -Seconds 2.5

# Abrir exclusivamente en Google Chrome o navegador predeterminado
Write-Host "Abriendo panel de control en Google Chrome..." -ForegroundColor Green
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
    Start-Process -FilePath $chromeExe -ArgumentList "http://localhost:8050"
} else {
    Start-Process "http://localhost:8050"
}

Write-Host ""
Write-Host ">> ALGORITMTRADING ROBOT ACTIVO Y FUNCIONANDO <<" -ForegroundColor Green
Write-Host "URL Dashboard: http://localhost:8050" -ForegroundColor Cyan
Write-Host "Documentacion API: http://localhost:8050/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "Para detener el servidor de trading, presiona Ctrl+C o cierra esta ventana." -ForegroundColor Gray

try {
    Wait-Process -Id $robotProc.Id
} catch {
    Stop-Process -Id $robotProc.Id -Force -ErrorAction SilentlyContinue
}
