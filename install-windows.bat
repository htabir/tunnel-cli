@echo off
REM Tunnel CLI Windows Installer (Batch Version)
REM This script installs Tunnel CLI on Windows

echo.
echo ========================================
echo    Tunnel CLI Installer for Windows
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo.
    echo Please install Python 3.8 or later from:
    echo https://www.python.org/downloads/
    echo.
    echo IMPORTANT: During installation, make sure to:
    echo   1. Check "Add Python to PATH"
    echo   2. Check "Install pip"
    echo.
    pause
    exit /b 1
)

echo [1/5] Python found
python --version

REM Upgrade pip
echo.
echo [2/5] Upgrading pip...
python -m pip install --upgrade pip --quiet

REM Install dependencies
echo.
echo [3/5] Installing dependencies...
python -m pip install --user textual aiohttp requests python-dotenv --quiet

REM Install Tunnel CLI from GitHub
echo.
echo [4/5] Installing Tunnel CLI...

REM Create temp directory
set TEMP_DIR=%TEMP%\tunnel-cli-install
if exist "%TEMP_DIR%" rmdir /s /q "%TEMP_DIR%"
mkdir "%TEMP_DIR%"

REM Download and install
cd /d "%TEMP_DIR%"
echo Downloading from GitHub...
curl -L https://github.com/htabir/tunnel-cli/archive/refs/heads/main.zip -o tunnel-cli.zip
if %errorlevel% neq 0 (
    echo ERROR: Failed to download. Trying with PowerShell...
    powershell -Command "Invoke-WebRequest -Uri 'https://github.com/htabir/tunnel-cli/archive/refs/heads/main.zip' -OutFile 'tunnel-cli.zip'"
)

echo Extracting...
tar -xf tunnel-cli.zip
cd tunnel-cli-main

echo Installing package...
python -m pip install --user .

REM Create convenient batch file
echo.
echo [5/5] Creating shortcuts...
echo @echo off > "%USERPROFILE%\tunnel.bat"
echo python -m tunnel_cli %%* >> "%USERPROFILE%\tunnel.bat"

REM Cleanup
cd /d "%USERPROFILE%"
rmdir /s /q "%TEMP_DIR%" 2>nul

REM Done
echo.
echo ========================================
echo    Installation Complete!
echo ========================================
echo.
echo To start Tunnel CLI, you can use any of these methods:
echo.
echo   1. Run: python -m tunnel_cli
echo   2. Run: %USERPROFILE%\tunnel
echo   3. After restarting terminal: tunnel
echo.
echo For help: tunnel --help
echo Portal: https://tunnel.ovream.com
echo.
pause