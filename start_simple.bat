@echo off
REM ============================================================
REM   Music Analysis Work - One-click Start
REM   Pure ASCII bat to avoid GBK/UTF-8 encoding issues
REM ============================================================

title Music Analysis Work - Starting
cd /d "E:\Music Analysis Work"

REM Use absolute Python path so this works even if PATH is not inherited
set PYTHON_EXE=C:\Users\22283\.workbuddy\binaries\python\versions\3.13.12\python.exe

REM Inherit system PATH (needed for netstat, tasklist, etc inside Python scripts)
set PATH=%SystemRoot%\system32;%SystemRoot%;%SystemRoot%\system32\Wbem;%PATH%

echo.
echo ============================================================
echo    Music Analysis Work
echo ============================================================
echo.
echo    [1/2] Restarting Flask with latest Apple Music UI...
"%PYTHON_EXE%" daemon.py restart
if errorlevel 1 (
    echo    [ERROR] Flask failed to start. Check flask.log
)

echo.
echo    [2/2] Starting cloudflared tunnel...
"%PYTHON_EXE%" scripts\start_cloudflared_detached.py
if errorlevel 1 (
    echo    [ERROR] cloudflared failed to start. Check cloudflared.log
)

echo.
echo ============================================================
echo    [OK] Both services started
echo ============================================================
echo.
echo    [Local URL]   http://127.0.0.1:5000
echo    [Music UI]    http://127.0.0.1:5000/player?ui=apple-music-v2
echo.

REM Open a cache-busted URL so the browser cannot reuse the old page.
start "" "http://127.0.0.1:5000/player?ui=apple-music-v2&v=%RANDOM%%RANDOM%"

if exist "public_url.txt" (
    echo    [Public URL - copy this to your friend]
    type "public_url.txt"
    echo.
) else (
    echo    [Public URL]  Not ready yet, wait 10s and check public_url.txt
    echo.
)

echo ============================================================
echo    Services are running. You can close this window.
echo    To stop later, run stop_simple.bat
echo ============================================================
echo.
echo    Press any key to close...
pause > nul
