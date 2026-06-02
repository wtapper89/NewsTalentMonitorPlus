$ErrorActionPreference = "Stop"

$runtimeCandidates = @(
    "C:\Program Files\NDI\NDI 6 Runtime\v6\Processing.NDI.Lib.x64.dll",
    "C:\Program Files\NDI\NDI 5 Runtime\v5\Processing.NDI.Lib.x64.dll",
    "C:\Program Files\NDI\NDI 5 Tools\Runtime\Processing.NDI.Lib.x64.dll"
)

foreach ($candidate in $runtimeCandidates) {
    if (Test-Path -LiteralPath $candidate) {
        Write-Host "NDI runtime is already installed:"
        Write-Host $candidate
        exit 0
    }
}

$redistUrl = "http://ndi.link/NDIRedistV6"
$downloadDir = Join-Path $env:TEMP "NewsTalentMonitorPlus"
$installerPath = Join-Path $downloadDir "NDI-Runtime-Installer.exe"

New-Item -ItemType Directory -Force -Path $downloadDir | Out-Null

Write-Host "Downloading the official NDI runtime installer..."
Write-Host $redistUrl

try {
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Invoke-WebRequest -Uri $redistUrl -OutFile $installerPath -UseBasicParsing
} catch {
    Write-Host ""
    Write-Host "Could not download the NDI runtime automatically."
    Write-Host "Opening the official NDI download page instead."
    Start-Process "https://ndi.video/for-developers/ndi-sdk/download/"
    exit 0
}

Write-Host ""
Write-Host "Starting the NDI runtime installer."
Write-Host "Complete the NDI installer prompts, then return here."

$process = Start-Process -FilePath $installerPath -Wait -PassThru

Write-Host ""
if ($process.ExitCode -eq 0) {
    Write-Host "NDI installer finished."
} else {
    Write-Host "NDI installer exited with code $($process.ExitCode)."
}

Write-Host ""
Write-Host "Checking NDI runtime..."
& (Join-Path $PSScriptRoot "NewsTalentMonitor.exe") --check-ndi
exit 0
