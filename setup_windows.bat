@echo off
setlocal
cd /d "%~dp0"

echo ==========================================
echo        TRUSTGUARD AI - WINDOWS SETUP
echo ==========================================

where py >nul 2>nul
if %errorlevel%==0 (
    py -3.11 -m venv .venv
) else (
    python -m venv .venv
)
if errorlevel 1 goto error

call .venv\Scripts\activate.bat
if errorlevel 1 goto error

python -m pip install --upgrade pip
if errorlevel 1 goto error

python -m pip install -r requirements.txt
if errorlevel 1 goto error

echo.
echo Setup complete. Run run_windows.bat to start TrustGuard AI.
pause
exit /b 0

:error
echo.
echo Setup failed. Check the error above. Ensure Python 3.11 is installed.
pause
exit /b 1
