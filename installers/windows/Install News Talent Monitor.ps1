$ErrorActionPreference = "Stop"

$ProductName = "News Talent Monitor+"
$InstallRoot = Join-Path $env:LOCALAPPDATA "NewsTalentMonitorPlus"
$SourceRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$PythonExe = $null

function Write-Section {
    param([string]$Text)
    Write-Host ""
    Write-Host "== $Text ==" -ForegroundColor Cyan
}

function Find-Python {
    $commands = @(
        @{ File = "py"; Args = @("-3") },
        @{ File = "python"; Args = @() },
        @{ File = "python3"; Args = @() }
    )

    foreach ($command in $commands) {
        try {
            $version = & $command.File @($command.Args + @("--version")) 2>$null
            if ($LASTEXITCODE -eq 0 -and $version -match "Python 3") {
                return @{
                    File = $command.File
                    Args = $command.Args
                }
            }
        } catch {
            continue
        }
    }

    throw "Python 3 was not found. Install Python 3 from https://www.python.org/downloads/windows/ and run this installer again."
}

function Invoke-Python {
    param([string[]]$Arguments)
    & $PythonExe.File @($PythonExe.Args + $Arguments)
}

Write-Host "$ProductName Windows installer"
Write-Host "This installs the app for the current Windows user."

Write-Section "Checking Python"
$PythonExe = Find-Python
Write-Host "Using Python command: $($PythonExe.File) $($PythonExe.Args -join ' ')"

Write-Section "Installing app files"
New-Item -ItemType Directory -Force -Path $InstallRoot | Out-Null
robocopy $SourceRoot $InstallRoot /MIR /XD ".git" ".venv" ".pi-image-build" "__pycache__" /XF ".DS_Store" | Out-Null
$robocopyCode = $LASTEXITCODE
if ($robocopyCode -gt 7) {
    throw "File copy failed with robocopy exit code $robocopyCode."
}

Write-Section "Creating Python environment"
Push-Location $InstallRoot
try {
    Invoke-Python @("-m", "venv", ".venv")
    $VenvPython = Join-Path $InstallRoot ".venv\Scripts\python.exe"
    & $VenvPython -m pip install --upgrade pip
    & $VenvPython -m pip install -r requirements.txt
} finally {
    Pop-Location
}

Write-Section "Preparing app data"
$DataRoot = Join-Path $env:APPDATA "NewsTalentMonitorPlus"
$FrameRoot = Join-Path $env:TEMP "NewsTalentMonitorPlus\ndi"
New-Item -ItemType Directory -Force -Path $DataRoot | Out-Null
New-Item -ItemType Directory -Force -Path $FrameRoot | Out-Null

$StartScript = Join-Path $InstallRoot "installers\windows\start-server.ps1"
$StopScript = Join-Path $InstallRoot "installers\windows\stop-server.ps1"
$OpenDisplayScript = Join-Path $InstallRoot "installers\windows\Open Display.bat"
$OpenConfigScript = Join-Path $InstallRoot "installers\windows\Open Config.bat"

Write-Section "Installing startup task"
$TaskName = "News Talent Monitor Plus"
$TaskAction = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$StartScript`""
$TaskTrigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$TaskSettings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Hours 0)
Register-ScheduledTask -TaskName $TaskName -Action $TaskAction -Trigger $TaskTrigger -Settings $TaskSettings -Description "Starts News Talent Monitor+ at Windows login." -Force | Out-Null

Write-Section "Creating shortcuts"
$Shell = New-Object -ComObject WScript.Shell
$Desktop = [Environment]::GetFolderPath("Desktop")

$Shortcut = $Shell.CreateShortcut((Join-Path $Desktop "News Talent Monitor+ Display.lnk"))
$Shortcut.TargetPath = $OpenDisplayScript
$Shortcut.WorkingDirectory = $InstallRoot
$Shortcut.Save()

$Shortcut = $Shell.CreateShortcut((Join-Path $Desktop "News Talent Monitor+ Config.lnk"))
$Shortcut.TargetPath = $OpenConfigScript
$Shortcut.WorkingDirectory = $InstallRoot
$Shortcut.Save()

$Shortcut = $Shell.CreateShortcut((Join-Path $Desktop "Stop News Talent Monitor+.lnk"))
$Shortcut.TargetPath = "powershell.exe"
$Shortcut.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$StopScript`""
$Shortcut.WorkingDirectory = $InstallRoot
$Shortcut.Save()

Write-Section "Checking NDI runtime"
Push-Location $InstallRoot
try {
    & $VenvPython tools\ndi\check_ndi_runtime.py
    $NdiStatus = $LASTEXITCODE
} finally {
    Pop-Location
}

if ($NdiStatus -ne 0) {
    Write-Host ""
    Write-Host "NDI is not ready yet." -ForegroundColor Yellow
    Write-Host "Install the official NDI runtime or SDK from:"
    Write-Host "https://ndi.video/for-developers/ndi-sdk/download/"
    Write-Host "Then restart News Talent Monitor+."
}

Write-Section "Starting app"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File $StartScript

Write-Host ""
Write-Host "Installed to: $InstallRoot"
Write-Host "Display: http://127.0.0.1:8010/display"
Write-Host "Config:  http://127.0.0.1:8010/config"
Write-Host ""
Write-Host "Press Enter to close this window."
Read-Host | Out-Null
