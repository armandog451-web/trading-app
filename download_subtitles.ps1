Set-Location "C:/Users/edsel/OneDrive/Documents/PROJET 2"
$urls = Get-Content "urls.txt"
foreach ($url in $urls) {
    if ($url.Trim() -eq "") { continue }
    Write-Host "Downloading subtitles for $url"
    yt-dlp.exe --skip-download --write-auto-sub --sub-lang es --convert-subs srt -o "%(title)s.%(ext)s" $url
    Start-Sleep -Seconds 15
}
Write-Host "All downloads completed"
