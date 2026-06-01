@echo off
setlocal
cd /d "%~dp0..\.."

echo News Talent Monitor+ Windows EXE installer builder
echo.

where python >nul 2>nul
if errorlevel 1 (
  echo Python 3 was not found.
  echo Install Python 3 from https://www.python.org/downloads/windows/
  exit /b 1
)

echo Installing/updating PyInstaller...
python -m pip install --upgrade pyinstaller
if errorlevel 1 exit /b 1

echo.
echo Building NewsTalentMonitor.exe...
python -m PyInstaller --noconfirm --clean installers\windows\NewsTalentMonitor.spec --distpath dist\windows --workpath .installer-build\pyinstaller
if errorlevel 1 exit /b 1

set "ISCC="
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not defined ISCC (
  where ISCC >nul 2>nul
  if not errorlevel 1 set "ISCC=ISCC"
)

if not defined ISCC (
  echo.
  echo Inno Setup 6 was not found.
  echo Install it from https://jrsoftware.org/isdl.php
  echo Then run this builder again.
  exit /b 1
)

echo.
echo Building installer EXE...
"%ISCC%" installers\windows\NewsTalentMonitorPlus.iss
if errorlevel 1 exit /b 1

echo.
echo Done.
echo Installer created at:
echo dist\windows-installer\NewsTalentMonitorPlus-Setup.exe
