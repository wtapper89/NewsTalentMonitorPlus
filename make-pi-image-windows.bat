@echo off
setlocal

where wsl >nul 2>nul
if errorlevel 1 (
  echo Windows Subsystem for Linux was not found.
  echo Install Ubuntu with: wsl --install -d Ubuntu
  echo Then restart this computer and run this file again.
  pause
  exit /b 1
)

where docker >nul 2>nul
if errorlevel 1 (
  echo Docker Desktop was not found on PATH.
  echo Install Docker Desktop, open it, and wait for the engine to start.
  pause
  exit /b 1
)

echo.
echo This will build the News Talent Monitor+ Raspberry Pi image.
echo Keep Docker Desktop open while it runs.
echo.

wsl bash -lc "cd \"$(wslpath '%CD%')\" && chmod +x ./make-pi-image.command ./deploy/pi-image/*.sh && ./make-pi-image.command"
if errorlevel 1 (
  echo.
  echo Image build failed. Check the messages above.
  pause
  exit /b 1
)

echo.
echo Done. Look in .pi-image-build\pi-gen\deploy for the newest .img.xz file.
pause
