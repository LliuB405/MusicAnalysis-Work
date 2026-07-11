@echo off
REM ============================================================
REM   Music Analysis Work - One-click Stop
REM   Pure ASCII bat
REM ============================================================

title Music Analysis Work - Stopping
cd /d "E:\Music Analysis Work"

set PYTHON_EXE=C:\Users\22283\.workbuddy\binaries\python\versions\3.13.12\python.exe

echo.
echo ============================================================
echo    Music Analysis Work - Stopping
echo ============================================================
echo.
echo    Stopping cloudflared...
taskkill /F /IM cloudflared.exe > nul 2>&1
echo    Stopping Flask...
"%PYTHON_EXE%" daemon.py stop

echo.
echo ============================================================
echo    [Done] All services stopped
echo ============================================================
echo.
pause
