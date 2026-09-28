# Script to create official desktop shortcut for AlgortimTrading Robot
$WshShell = New-Object -ComObject WScript.Shell
$desktopPaths = @(
    [Environment]::GetFolderPath('Desktop'),
    "$env:USERPROFILE\OneDrive\Desktop",
    "$env:USERPROFILE\Desktop"
) | Select-Object -Unique

# Target files
$targetBat = "C:\Users\edsel\OneDrive\Documents\PROJET 2\start.bat"
$workingDir = "C:\Users\edsel\OneDrive\Documents\PROJET 2"
$iconFile = "C:\Users\edsel\OneDrive\Documents\PROJET 2\app_icon.ico"

foreach ($d in $desktopPaths) {
    if (Test-Path $d) {
        # Clean up older broken files if they exist
        Remove-Item (Join-Path $d "AlgortimTradingBot.lnk") -Force -ErrorAction SilentlyContinue
        Remove-Item (Join-Path $d "AlgortimTradingBot.bat") -Force -ErrorAction SilentlyContinue

        # Create the new official shortcut
        $shortcutPath = Join-Path $d "AlgortimTrading Robot.lnk"
        $shortcut = $WshShell.CreateShortcut($shortcutPath)
        $shortcut.TargetPath = $targetBat
        $shortcut.WorkingDirectory = $workingDir
        if (Test-Path $iconFile) {
            $shortcut.IconLocation = "$iconFile,0"
        }
        $shortcut.Save()
        Write-Host "Acceso directo creado exitosamente en: $shortcutPath"
    }
}
