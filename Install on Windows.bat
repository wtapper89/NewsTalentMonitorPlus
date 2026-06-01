@echo off
setlocal
cd /d "%~dp0"

if exist "%~dp0NewsTalentMonitorPlus-Setup.exe" (
  start "" "%~dp0NewsTalentMonitorPlus-Setup.exe"
  exit /b 0
)

if exist "%~dp0dist\windows-installer\NewsTalentMonitorPlus-Setup.exe" (
  start "" "%~dp0dist\windows-installer\NewsTalentMonitorPlus-Setup.exe"
  exit /b 0
)

echo News Talent Monitor+ now uses a Windows installer EXE.
echo.
echo If you downloaded a release, run:
echo   NewsTalentMonitorPlus-Setup.exe
echo.
echo If you are building from source on Windows, run:
echo   installers\windows\Build Windows Installer.bat
echo.
pause
