$ErrorActionPreference = "Stop"

$DataRoot = Join-Path $env:APPDATA "NewsTalentMonitorPlus"
$PidPath = Join-Path $DataRoot "server.pid"

if (-not (Test-Path $PidPath)) {
    Write-Host "News Talent Monitor+ is not running."
    exit 0
}

$ProcessId = Get-Content $PidPath -ErrorAction SilentlyContinue
if ($ProcessId) {
    $Process = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
    if ($Process) {
        Stop-Process -Id $ProcessId -Force
        Write-Host "Stopped News Talent Monitor+."
    }
}

Remove-Item $PidPath -Force -ErrorAction SilentlyContinue
