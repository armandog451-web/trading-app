# AlgortimTrading Robot v2.0 - Lanzador Unificado
$ErrorActionPreference = "Stop"

$rootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$py311 = "C:\Users\edsel\AppData\Local\Programs\Python\Python311\python.exe"

if (Test-Path $py311) {
    $pyExe = $py311
    $env:Path = "C:\Users\edsel\AppData\Local\Programs\Python\Python311;C:\Users\edsel\AppData\Local\Programs\Python\Python311\Scripts;" + $env:Path
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $pyExe = (Get-Command python).Source
} else {
    $pyExe = "python.exe"
}

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " AlgortimTrading Robot v2.0 - Entorno Cuantitativo" -ForegroundColor Green
Write-Host " Estrategia Hibrida Intradia (Alpaca & Moomoo + Telegram)" -ForegroundColor White
Write-Host "==========================================================" -ForegroundColor Cyan

Write-Host "Iniciando AlgortimTrading Robot en http://localhost:8050..." -ForegroundColor Yellow

# Iniciar servidor backend unificado
$backendProc = Start-Process -FilePath $pyExe -ArgumentList "server.py" -WorkingDirectory $rootDir -PassThru

# Esperar 2.5 segundos para arranque del servidor
Start-Sleep -Seconds 2.5

# Abrir exclusivamente en Google Chrome
Write-Host "Abriendo terminal de control en Google Chrome..." -ForegroundColor Green
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
Write-Host ">> APLICACION ACTIVA Y FUNCIONANDO <<" -ForegroundColor Green
Write-Host "URL Dashboard: http://localhost:8050" -ForegroundColor Cyan
Write-Host "Telegram Bot: @LaraMayaBot (Sincronizado)" -ForegroundColor Cyan
Write-Host ""
Write-Host "Para detener el robot, presiona Ctrl+C o cierra esta ventana." -ForegroundColor Gray

try {
    Wait-Process -Id $backendProc.Id
} catch {
    Stop-Process -Id $backendProc.Id -Force -ErrorAction SilentlyContinue
}
