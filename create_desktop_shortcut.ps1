# Script to create official desktop shortcuts for AlgortimTrading Robot & TradePulse
$WshShell = New-Object -ComObject WScript.Shell
$desktopPaths = @(
    [Environment]::GetFolderPath('Desktop'),
    "$env:USERPROFILE\OneDrive\Desktop",
    "$env:USERPROFILE\Desktop"
) | Select-Object -Unique

# Target files
$workingDir = "C:\Users\edsel\OneDrive\Documents\PROJET 2"
$robotBat = Join-Path $workingDir "start.bat"
$tradepulseBat = Join-Path $workingDir "start_tradepulse.bat"
$iconFile = Join-Path $workingDir "app_icon.ico"

foreach ($d in $desktopPaths) {
    if (Test-Path $d) {
        # Clean up older broken files if they exist
        Remove-Item (Join-Path $d "AlgortimTradingBot.lnk") -Force -ErrorAction SilentlyContinue
        Remove-Item (Join-Path $d "AlgortimTradingBot.bat") -Force -ErrorAction SilentlyContinue

        # 1. Acceso Directo Oficial: AlgortimTrading Robot
        $robotShortcutPath = Join-Path $d "AlgortimTrading Robot.lnk"
        $robotShortcut = $WshShell.CreateShortcut($robotShortcutPath)
        $robotShortcut.TargetPath = $robotBat
        $robotShortcut.WorkingDirectory = $workingDir
        if (Test-Path $iconFile) {
            $robotShortcut.IconLocation = "$iconFile,0"
        }
        $robotShortcut.Save()
        Write-Host "Acceso directo AlgortimTrading Robot actualizado en: $robotShortcutPath"

        # 2. Acceso Directo Oficial: TradePulse Engine
        $tpShortcutPath = Join-Path $d "TradePulse Engine.lnk"
        $tpShortcut = $WshShell.CreateShortcut($tpShortcutPath)
        $tpShortcut.TargetPath = $tradepulseBat
        $tpShortcut.WorkingDirectory = $workingDir
        if (Test-Path $iconFile) {
            $tpShortcut.IconLocation = "$iconFile,0"
        }
        $tpShortcut.Save()
        Write-Host "Acceso directo TradePulse Engine creado en: $tpShortcutPath"

        # 3. Acceso Directo Oficial: AI Trading Agent SuperRobot
        $superRobotBat = Join-Path $workingDir "start_superrobot.bat"
        $srShortcutPath = Join-Path $d "AI Trading Agent SuperRobot.lnk"
        $srShortcut = $WshShell.CreateShortcut($srShortcutPath)
        $srShortcut.TargetPath = $superRobotBat
        $srShortcut.WorkingDirectory = $workingDir
        if (Test-Path $iconFile) {
            $srShortcut.IconLocation = "$iconFile,0"
        }
        $srShortcut.Save()
        Write-Host "Acceso directo AI Trading Agent SuperRobot creado en: $srShortcutPath"
    }
}
