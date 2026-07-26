@echo off
chcp 65001 >nul
setlocal EnableExtensions

cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0MusicAnalysis-Stop.ps1"
set "EXIT_CODE=%ERRORLEVEL%"

if not "%EXIT_CODE%"=="0" (
    echo Stop failed. Review the complete error message above.
    pause
)

endlocal & exit /b %EXIT_CODE%
