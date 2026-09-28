# create_shortcut.ps1
# PowerShell script to create a desktop shortcut for the trading bot (run_bot.bat)

$Shell = New-Object -ComObject WScript.Shell
$Desktop = [Environment]::GetFolderPath('Desktop')
$ShortcutPath = Join-Path $Desktop "AlgortimTradingBot.lnk"
$TargetPath = "C:\\Users\\edsel\\OneDrive\\Documents\\PROJET 2\\run_bot.bat"
$WorkingDir = "C:\\Users\\edsel\\OneDrive\\Documents\\PROJET 2"
$Shortcut = $Shell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $TargetPath
$Shortcut.WorkingDirectory = $WorkingDir
$Shortcut.IconLocation = "C:\\Windows\\System32\\imageres.dll,3"
$Shortcut.Save()
Write-Host "Shortcut created at $ShortcutPath"
