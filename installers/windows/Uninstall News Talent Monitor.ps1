$ErrorActionPreference = "Stop"

$TaskName = "News Talent Monitor Plus"
$InstallRoot = Join-Path $env:LOCALAPPDATA "NewsTalentMonitorPlus"
$DataRoot = Join-Path $env:APPDATA "NewsTalentMonitorPlus"
$Desktop = [Environment]::GetFolderPath("Desktop")

$StopScript = Join-Path $InstallRoot "installers\windows\stop-server.ps1"
if (Test-Path $StopScript) {
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File $StopScript
}

Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

Remove-Item (Join-Path $Desktop "News Talent Monitor+ Display.lnk") -Force -ErrorAction SilentlyContinue
Remove-Item (Join-Path $Desktop "News Talent Monitor+ Config.lnk") -Force -ErrorAction SilentlyContinue
Remove-Item (Join-Path $Desktop "Stop News Talent Monitor+.lnk") -Force -ErrorAction SilentlyContinue

Remove-Item $InstallRoot -Recurse -Force -ErrorAction SilentlyContinue

Write-Host "News Talent Monitor+ app files were removed."
Write-Host "User data remains here so settings are not accidentally lost:"
Write-Host $DataRoot
Write-Host ""
Write-Host "Delete that folder manually if you want to remove settings and logs too."
Read-Host "Press Enter to close" | Out-Null
