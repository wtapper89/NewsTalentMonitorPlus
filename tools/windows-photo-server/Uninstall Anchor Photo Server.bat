@echo off
schtasks /Delete /F /TN "News Talent Monitor Photo Server"
schtasks /Delete /F /TN "Anchor Mics Photo Server" >nul 2>nul
echo News Talent Monitor+ photo server startup task removed.
pause
