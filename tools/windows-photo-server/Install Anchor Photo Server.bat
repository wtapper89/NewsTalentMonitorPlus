@echo off
setlocal

set "PORT=8090"
set "TASK_NAME=Anchor Mics Photo Server"
set "PHOTO_DIR=%~dp0"
set "START_SCRIPT=%PHOTO_DIR%Start Anchor Photo Server.vbs"

where python >nul 2>nul
if errorlevel 1 (
  echo Python was not found. Install Python, then run this again.
  pause
  exit /b 1
)

echo Creating startup task: %TASK_NAME%
echo Photo folder: %PHOTO_DIR%
echo Port: %PORT%

schtasks /Create /F /TN "%TASK_NAME%" /SC ONLOGON /RL LIMITED /TR "wscript.exe \"\"%START_SCRIPT%\"\"" >nul
if errorlevel 1 (
  echo Failed to create the scheduled task.
  echo Try right-clicking this file and choosing Run as administrator.
  pause
  exit /b 1
)

schtasks /Run /TN "%TASK_NAME%" >nul

echo.
echo Done. The photo server will start when this Windows user logs in.
echo URL for Anchor Mics:
echo http://%COMPUTERNAME%:%PORT%/
echo.
echo Put files like JohnSmith.png, JohnSmith.jpg, or JohnSmith.jpeg in:
echo %PHOTO_DIR%
pause
