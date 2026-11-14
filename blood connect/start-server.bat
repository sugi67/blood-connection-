

@echo off
setlocal enabledelayedexpansion
title BloodConnect Backend Server Launcher

echo =======================================================
echo          BloodConnect Emergency Blood Network
echo                 Backend Server Launcher
echo =======================================================
echo.

set PORT=5000
if not "%~1"=="" set PORT=%~1

set PYTHON_CMD=

:: 1. Check LibreOffice bundled Python 3.11 (verified on this machine)
if exist "C:\Program Files\LibreOffice\program\python.exe" (
    set "PYTHON_CMD=C:\Program Files\LibreOffice\program\python.exe"
    goto :FOUND
)

:: 2. Check py launcher
py -3 -c "import sys; print(sys.version)" >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=py -3"
    goto :FOUND
)

:: 3. Check python on PATH
python -c "import sys; print(sys.version)" >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=python"
    goto :FOUND
)

echo [!] Error: No working Python 3 installation was detected.
echo     Please install Python 3.10+ from https://python.org
echo.
pause
exit /b 1

:FOUND
echo [*] Using Python Runtime: !PYTHON_CMD!
echo [*] Starting BloodConnect REST API & Static Server on http://localhost:%PORT%/
echo [*] Press Ctrl+C in this console to stop the server anytime.
echo.

:: Launch default browser after 1 second delay in background
start "" cmd /c "timeout /t 2 /nobreak >nul & start http://localhost:%PORT%/"

:: Run the backend server
"!PYTHON_CMD!" backend\server.py %PORT%

if errorlevel 1 (
    echo.
    echo [!] Server exited with an error code: %errorlevel%
    pause
)
