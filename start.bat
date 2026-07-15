@echo off
chcp 65001 >nul
setlocal

cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0MusicAnalysis-Start.ps1"
set "EXIT_CODE=%ERRORLEVEL%"

echo.
if not "%EXIT_CODE%"=="0" (
    echo Startup failed. Review the message above.
    pause
) else (
    echo Startup complete. This window will close in 8 seconds.
    powershell.exe -NoProfile -Command "Start-Sleep -Seconds 8"
)

endlocal & exit /b %EXIT_CODE%
