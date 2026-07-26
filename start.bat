@echo off
chcp 65001 >nul
setlocal EnableExtensions

cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0MusicAnalysis-Start.ps1"
set "EXIT_CODE=%ERRORLEVEL%"

echo.
if not "%EXIT_CODE%"=="0" (
    echo Startup failed. Review the complete error message above.
) else (
    echo Startup complete. The browser and background services can keep running.
)
echo Press any key to close this window.
pause >nul

endlocal & exit /b %EXIT_CODE%
