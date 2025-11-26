@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1

set SCRIPT_DIR=%~dp0
set HOST_URL=http://localhost:5000
set PYTHON_DIR=%SCRIPT_DIR%python
set PYTHON_EXE=%PYTHON_DIR%\python.exe
set PYTHON_ZIP=%SCRIPT_DIR%python.zip
set PYTHON_URL=https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip
set GET_PIP_URL=https://bootstrap.pypa.io/get-pip.py

echo ========================================
echo   WebM Metadata Editor - Launcher
echo ========================================
echo.

:: Check if portable Python exists
if exist "%PYTHON_EXE%" (
    echo [OK] Portable Python found.
    goto :check_deps
)

:: Check if system Python exists
where python >nul 2>&1
if %errorlevel%==0 (
    echo [OK] System Python found.
    set PYTHON_EXE=python
    goto :run_server
)

:: No Python found - download portable version
echo [!] Python not found. Downloading portable Python...
echo.

:: Download Python embeddable package
echo Downloading Python 3.11.9 embeddable...
curl -L -o "%PYTHON_ZIP%" "%PYTHON_URL%"
if %errorlevel% neq 0 (
    echo [ERROR] Failed to download Python. Check your internet connection.
    pause
    exit /b 1
)

:: Extract Python
echo Extracting Python...
mkdir "%PYTHON_DIR%" 2>nul
powershell -Command "Expand-Archive -Path '%PYTHON_ZIP%' -DestinationPath '%PYTHON_DIR%' -Force"
if %errorlevel% neq 0 (
    echo [ERROR] Failed to extract Python.
    pause
    exit /b 1
)

:: Delete zip file
del "%PYTHON_ZIP%" 2>nul

:: Enable pip in embedded Python (modify python311._pth)
echo Configuring Python for pip...
set PTH_FILE=%PYTHON_DIR%\python311._pth
if exist "%PTH_FILE%" (
    echo python311.zip> "%PTH_FILE%"
    echo .>> "%PTH_FILE%"
    echo Lib\site-packages>> "%PTH_FILE%"
    echo import site>> "%PTH_FILE%"
)

:: Download and install pip
echo Installing pip...
curl -L -o "%PYTHON_DIR%\get-pip.py" "%GET_PIP_URL%"
if %errorlevel% neq 0 (
    echo [ERROR] Failed to download pip installer.
    pause
    exit /b 1
)

"%PYTHON_EXE%" "%PYTHON_DIR%\get-pip.py" --no-warn-script-location
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install pip.
    pause
    exit /b 1
)

del "%PYTHON_DIR%\get-pip.py" 2>nul

echo [OK] Portable Python installed successfully!
echo.

:check_deps
:: Install dependencies if needed
if exist "%PYTHON_DIR%\Lib\site-packages\flask" (
    echo [OK] Dependencies already installed.
    goto :run_server
)

echo Installing dependencies...
"%PYTHON_EXE%" -m pip install -r "%SCRIPT_DIR%requirements.txt" --no-warn-script-location -q
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)
echo [OK] Dependencies installed.
echo.

:run_server
echo Starting server...
echo.

:: Check if app.py exists
if not exist "%SCRIPT_DIR%app.py" (
    echo [ERROR] app.py not found in %SCRIPT_DIR%
    echo Please make sure you extracted all files correctly.
    pause
    exit /b 1
)

:: Install dependencies for system Python too
if "%PYTHON_EXE%"=="python" (
    echo Checking dependencies...
    python -m pip install Flask Werkzeug -q 2>nul
)

start "WebM Metadata Editor" cmd /k "cd /d %SCRIPT_DIR% && echo Current folder: %SCRIPT_DIR% && echo. && dir app.py 2>nul || echo [ERROR] app.py NOT FOUND in this folder! && echo. && "%PYTHON_EXE%" app.py & echo. & echo ======================================== & echo Server stopped or failed. See error above. & echo ======================================== & pause"

echo Waiting for server...
timeout /t 2 >nul

echo Opening %HOST_URL% in browser...
start "" "%HOST_URL%"

echo.
echo ========================================
echo   Server is running at %HOST_URL%
echo   Close the server window to stop.
echo ========================================
echo.
echo Press any key to close this window...
pause >nul
