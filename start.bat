@echo off
chcp 65001 >nul
setlocal

REM ============================================================
REM   Music Analysis Work 一键启动脚本
REM   作用：启动 Flask + Cloudflared 隧道，让朋友能从公网访问
REM   用法：双击运行（或右键 → 以管理员身份运行）
REM   作者：Senior Developer
REM ============================================================

cd /d "E:\Music Analysis Work"

echo.
echo ============================================================
echo    Music Analysis Work  启动中...
echo ============================================================
echo.

REM ---------- 第 1 步：检查 Python ----------
where python >nul 2>&1
if errorlevel 1 (
    echo [错误] 找不到 Python，请确认 Python 已安装并加入 PATH
    pause
    exit /b 1
)

REM ---------- 第 2 步：检查 cloudflared ----------
if not exist "C:\Users\22283\.workbuddy\binaries\cloudflared.exe" (
    echo [警告] 未找到 cloudflared, 正在下载...
    powershell -NoProfile -Command "Invoke-WebRequest -Uri 'https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe' -OutFile 'C:\Users\22283\.workbuddy\binaries\cloudflared.exe'"
    if errorlevel 1 (
        echo [错误] cloudflared 下载失败。请检查网络（建议连手机热点）后重试
        pause
        exit /b 1
    )
    echo [成功] cloudflared 已下载
)

REM ---------- 第 3 步：强制重启，确保加载最新模板 ----------
echo [1/2] 正在重启 Flask 并加载最新版 Apple Music 界面...
python daemon.py restart
if errorlevel 1 (
    echo [错误] Flask 重启失败，请检查 flask.err.log
    pause
    exit /b 1
)
timeout /t 2 /nobreak >nul

REM ---------- 第 4 步：检查 cloudflared 是否在跑 ----------
tasklist /FI "IMAGENAME eq cloudflared.exe" 2>nul | find /I "cloudflared.exe" >nul
if not errorlevel 1 (
    echo [提示] cloudflared 已在运行
    echo        如需新 URL，请先结束现有进程：taskkill /F /IM cloudflared.exe
) else (
    echo [2/2] 启动 cloudflared 隧道...
    REM 清理旧日志
    if exist "cloudflared.log" del "cloudflared.log"
    start "Cloudflared" /B "" python "scripts\start_cloudflared_detached.py"
    REM 等待 cloudflared 注册 + 输出 URL
    echo        等待 Cloudflare 分配 URL （约 10 秒）...
    timeout /t 12 /nobreak >nul
)

REM ---------- 第 5 步：读取并显示新 URL ----------
echo.
echo ============================================================
echo    [启动完成]
echo ============================================================
echo.
if exist "cloudflared.log" (
    echo [公网 URL]
    findstr /C:"trycloudflare.com" "cloudflared.log" >nul
    if not errorlevel 1 (
        for /f "tokens=*" %%i in ('findstr /C:"trycloudflare.com" "cloudflared.log"') do (
            echo   %%i
        )
    ) else (
        echo    尚未生成 URL，请检查 cloudflared.log
        echo    或访问 http://127.0.0.1:5000 本地测试
    )
) else (
    echo    暂无 cloudflared 日志
)
echo.
echo [本地访问]  http://127.0.0.1:5000
echo [新版听歌]  http://127.0.0.1:5000/player?ui=apple-music-v2
echo.
start "" "http://127.0.0.1:5000/player?ui=apple-music-v2&v=%RANDOM%%RANDOM%"
echo [提示]
echo    - 朋友第一次打开公网 URL 需点 "Visit Site"
echo    - 手机访问需用浏览器打开（不能用微信内置）
echo    - 关电脑或关闭本进程 = 链接失效
echo.
echo [关闭服务] 双击 "MusicAnalysis-关闭.bat"
echo.
echo 按任意键关闭此窗口（不会关闭后台服务）...
pause >nul
endlocal
