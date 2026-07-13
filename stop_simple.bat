@echo off
REM ============================================================
REM   Music Analysis Work - One-click Stop
REM   Pure ASCII bat
REM ============================================================

title Music Analysis Work - Stopping
cd /d "%~dp0"

set "PYTHON_EXE=python"
where python > nul 2>&1
if errorlevel 1 (
    echo    [ERROR] Python was not found in PATH.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo    Music Analysis Work - Stopping
echo ============================================================
echo.
echo    Stopping cloudflared...
if exist "cloudflared.pid" (
    for /f "usebackq delims=" %%p in ("cloudflared.pid") do taskkill /PID %%p /T /F > nul 2>&1
    del /q "cloudflared.pid" > nul 2>&1
)
echo    Stopping Flask...
"%PYTHON_EXE%" daemon.py stop

echo.
echo ============================================================
echo    [Done] All services stopped
echo ============================================================
echo.
pause
