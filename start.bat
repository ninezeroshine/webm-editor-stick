@echo off
setlocal

set SCRIPT_DIR=%~dp0
set HOST_URL=http://localhost:5000

echo Starting WebM Metadata Editor server...
start "WebM Metadata Editor" cmd /k "cd /d %SCRIPT_DIR% && python app.py"

echo Waiting for server to become available...
timeout /t 2 >nul

echo Opening %HOST_URL% in your default browser...
start "" "%HOST_URL%"

echo Done. Press any key to close this window.
pause >nul
