@echo off
chcp 65001 >nul
REM ============================================================
REM   开机自启动安装器
REM   作用：把"启动.bat"放到 Windows 启动文件夹
REM   开机后自动运行 Flask + cloudflared
REM   卸载：删除 "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\MusicAnalysis-启动.lnk"
REM ============================================================

set STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
set TARGET="E:\Music Analysis Work\start.bat"
set SHORTCUT="%STARTUP_DIR%\MusicAnalysis-启动.lnk"

echo.
echo ============================================================
echo    Music Analysis Work  开机自启动安装器
echo ============================================================
echo.
echo 目标位置：%SHORTCUT%
echo.

REM 用 PowerShell 创建快捷方式
powershell -NoProfile -Command ^
    "$ws = New-Object -ComObject WScript.Shell; ^
     $s = $ws.CreateShortcut('%SHORTCUT%'); ^
     $s.TargetPath = 'E:\Music Analysis Work\start.bat'; ^
     $s.WorkingDirectory = 'E:\Music Analysis Work'; ^
     $s.WindowStyle = 7; ^
     $s.Description = 'Music Analysis Work - 启动 Flask + Cloudflared'; ^
     $s.Save(); ^
     Write-Host '[成功] 已创建开机启动快捷方式'"

if errorlevel 1 (
    echo [错误] 创建失败，请用管理员身份运行
) else (
    echo.
    echo [效果] 每次开机后会自动启动 Flask + cloudflared
    echo [注意] 开机启动需要联网，建议电脑常连手机热点或常驻 WiFi
    echo.
    echo [卸载] 删掉这个文件即可：
    echo        %SHORTCUT%
)
echo.
pause
