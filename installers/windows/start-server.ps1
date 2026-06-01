$ErrorActionPreference = "Stop"

$InstallRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$VenvPython = Join-Path $InstallRoot ".venv\Scripts\python.exe"
$DataRoot = Join-Path $env:APPDATA "NewsTalentMonitorPlus"
$FrameRoot = Join-Path $env:TEMP "NewsTalentMonitorPlus\ndi"
$LogPath = Join-Path $DataRoot "news-talent-monitor.log"
$PidPath = Join-Path $DataRoot "server.pid"

New-Item -ItemType Directory -Force -Path $DataRoot | Out-Null
New-Item -ItemType Directory -Force -Path $FrameRoot | Out-Null

if (Test-Path $PidPath) {
    $ExistingPid = Get-Content $PidPath -ErrorAction SilentlyContinue
    if ($ExistingPid) {
        $ExistingProcess = Get-Process -Id $ExistingPid -ErrorAction SilentlyContinue
        if ($ExistingProcess) {
            Write-Host "News Talent Monitor+ is already running on process $ExistingPid."
            exit 0
        }
    }
}

$env:ANCHOR_MICS_HOST = "127.0.0.1"
$env:ANCHOR_MICS_PORT = "8010"
$env:ANCHOR_MICS_DATA_FILE = Join-Path $DataRoot "state.json"
$env:ANCHOR_MICS_LOG_FILE = $LogPath
$env:ANCHOR_MICS_NDI_WORK_DIR = $FrameRoot

$Process = Start-Process -FilePath $VenvPython -ArgumentList "run.py" -WorkingDirectory $InstallRoot -WindowStyle Hidden -PassThru
Set-Content -Path $PidPath -Value $Process.Id
Write-Host "Started News Talent Monitor+ on process $($Process.Id)."
