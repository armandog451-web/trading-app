# auto_start_trading_agent.ps1
# Lanzador maestro autónomo para recuperación y auto-inicio con Windows Task Scheduler
$ErrorActionPreference = "Continue"

$repoDir = "C:\Users\edsel\Documents\trading-app-repo"
$venvPy = Join-Path $repoDir ".venv\Scripts\python.exe"
$env:PYTHONPATH = $repoDir

# 1. Esperar disponibilidad de red (máximo 30s)
$netOk = $false
for ($i = 0; $i -lt 15; $i++) {
    if (Test-Connection -ComputerName 127.0.0.1 -Count 1 -Quiet) {
        $netOk = $true
        break
    }
    Start-Sleep -Seconds 2
}

# 2. Intento de inicio de Moomoo OpenD
$openDExe = "C:\Users\edsel\AppData\Roaming\moomoo_OpenD\moomoo_OpenD.exe"
$openDDir = "C:\Users\edsel\AppData\Roaming\moomoo_OpenD"
if (Test-Path $openDExe) {
    $runningOpenD = Get-Process -Name "*moomoo_OpenD*" -ErrorAction SilentlyContinue
    if (-not $runningOpenD) {
        Start-Process -FilePath $openDExe -WorkingDirectory $openDDir -WindowStyle Minimized -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 3
    }
}

# 3. Verificación de Single Instance para AI Trading Agent (Puerto 8090)
$port8090 = Get-NetTCPConnection -LocalPort 8090 -State Listen -ErrorAction SilentlyContinue
if (-not $port8090) {
    Start-Process -FilePath $venvPy -ArgumentList "run_superrobot.py" -WorkingDirectory $repoDir -WindowStyle Hidden
    Start-Sleep -Seconds 5
}

# 4. Verificación de Single Instance para EXP-ST02 Daemon
$st02Script = Join-Path $repoDir "ai_trading_agent\strategy_lab\experiments\exp_st02\run_st02_service.py"
$runningST02 = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "*run_st02_service.py*--daemon*" }
if (-not $runningST02) {
    Start-Process -FilePath $venvPy -ArgumentList "$st02Script --daemon" -WorkingDirectory $repoDir -WindowStyle Hidden
    Start-Sleep -Seconds 3
}

# 5. Verificación de Salud
$healthOk = $false
try {
    $resp = Invoke-RestMethod -Uri "http://127.0.0.1:8090/health" -TimeoutSec 5
    if ($resp.status -eq "HEALTHY") {
        $healthOk = $true
    }
} catch {}

Write-Host "Auto-start sequence completed. Health OK: $healthOk"
