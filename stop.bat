@echo off
chcp 65001 >nul
setlocal

cd /d "E:\Music Analysis Work"

echo.
echo ============================================================
echo    Music Analysis Work  关闭中...
echo ============================================================
echo.

REM 关闭 cloudflared
echo [1/2] 关闭 cloudflared...
taskkill /F /IM cloudflared.exe >nul 2>&1
if errorlevel 1 (
    echo        cloudflared 未运行
) else (
    echo        cloudflared 已关闭
)

REM 关闭 Flask（用 daemon.py 的 stop 子命令）
echo [2/2] 关闭 Flask...
python daemon.py stop >nul 2>&1
echo        Flask 已关闭

echo.
echo [完成] 所有服务已停止。公网 URL 已失效。
echo.
pause
endlocal
