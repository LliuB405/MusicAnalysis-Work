@echo off
chcp 65001 >nul
setlocal

cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0MusicAnalysis-Stop.ps1"
set "EXIT_CODE=%ERRORLEVEL%"

if not "%EXIT_CODE%"=="0" pause
endlocal & exit /b %EXIT_CODE%
