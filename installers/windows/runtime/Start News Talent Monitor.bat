@echo off
setlocal
set "APP_DIR=%~dp0"
set "APP_DATA=%APPDATA%\NewsTalentMonitorPlus"
set "APP_TEMP=%TEMP%\NewsTalentMonitorPlus"

if not exist "%APP_DATA%" mkdir "%APP_DATA%"
if not exist "%APP_TEMP%\ndi" mkdir "%APP_TEMP%\ndi"

set "ANCHOR_MICS_HOST=127.0.0.1"
set "ANCHOR_MICS_PORT=8010"
set "ANCHOR_MICS_DATA_FILE=%APP_DATA%\state.json"
set "ANCHOR_MICS_LOG_FILE=%APP_DATA%\news-talent-monitor.log"
set "ANCHOR_MICS_NDI_WORK_DIR=%APP_TEMP%\ndi"

start "News Talent Monitor+" "%APP_DIR%NewsTalentMonitor.exe" --tray
