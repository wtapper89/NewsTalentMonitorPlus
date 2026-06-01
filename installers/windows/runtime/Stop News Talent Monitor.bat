@echo off
taskkill /F /IM NewsTalentMonitor.exe >nul 2>nul
if errorlevel 1 (
  echo News Talent Monitor+ was not running.
) else (
  echo News Talent Monitor+ stopped.
)
pause
