@echo off
echo ========================================
echo Installing YourApp Windows Service
echo ========================================
echo.

REM Check if running as administrator
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: This script must be run as Administrator
    echo Right-click and select "Run as administrator"
    pause
    exit /b 1
)

echo [1] Activating virtual environment...
call venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo ERROR: Failed to activate virtual environment
    pause
    exit /b 1
)

echo.
echo [2] Installing service...
python service_manager.py install
if %errorlevel% neq 0 (
    echo ERROR: Service installation failed
    pause
    exit /b 1
)

echo.
echo [3] Starting service...
python service_manager.py start
if %errorlevel% neq 0 (
    echo WARNING: Service start failed, but service is installed
)

echo.
echo [4] Checking service status...
python service_manager.py status

echo.
echo ========================================
echo Installation Complete!
echo ========================================
echo.
echo You can now check the service in:
echo - Services (services.msc)
echo - Or run: Get-Service -Name "YourAppService"
echo.
pause