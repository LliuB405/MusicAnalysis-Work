# Music Analysis Work - One-click Launcher (PowerShell)
# 作用：启动 Flask + cloudflared 隧道，让朋友从公网访问
# 用法：右键 → "使用 PowerShell 运行"，或桌面快捷方式指向本脚本
#
# 注意：不要用 -WindowStyle Hidden 启动，会看不到输出！
# 推荐：右键桌面 → 新建快捷方式 → 位置填：
#   powershell.exe -NoProfile -ExecutionPolicy Bypass -File "<项目目录>\MusicAnalysis-Start.ps1"

$ErrorActionPreference = "Continue"
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ProjectDir = $PSScriptRoot
$CloudflaredDir = Join-Path $ProjectDir "scripts\bin"
$Cloudflared = Join-Path $CloudflaredDir "cloudflared.exe"
$LogFile = Join-Path $ProjectDir "cloudflared.log"
$FlaskLog = Join-Path $ProjectDir "flask.log"
$OutputLog = Join-Path $ProjectDir "start_output.log"   # 本脚本输出也留一份
$PublicUrlFile = Join-Path $ProjectDir "public_url.txt" # 最新公网 URL

Set-Location $ProjectDir

# 把所有输出同时写到 console + log 文件
Start-Transcript -Path $OutputLog -Append -Force | Out-Null

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "   Music Analysis Work  Starting..." -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# ---------- Step 1: Check Python ----------
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) {
    Write-Host "[ERROR] Python not found in PATH" -ForegroundColor Red
    Write-Host ""
    Write-Host "Press Enter to close..." -ForegroundColor Gray
    Read-Host
    exit 1
}
Write-Host "[OK] Python found: $($py.Source)" -ForegroundColor Green

# ---------- Step 2: Download cloudflared if missing ----------
if (-not (Test-Path $Cloudflared)) {
    Write-Host "[INFO] cloudflared not found, downloading..." -ForegroundColor Yellow
    try {
        New-Item -ItemType Directory -Path $CloudflaredDir -Force | Out-Null
        Invoke-WebRequest -Uri "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe" -OutFile $Cloudflared -UseBasicParsing
        Write-Host "[OK] cloudflared downloaded" -ForegroundColor Green
    } catch {
        Write-Host "[ERROR] Download failed. Check network (try phone hotspot)." -ForegroundColor Red
        Write-Host ""
        Write-Host "Press Enter to close..." -ForegroundColor Gray
        Read-Host
        exit 1
    }
}

# ---------- Step 3: Restart Flask so UI/template updates are loaded ----------
Write-Host "[1/2] Restarting Flask with the latest Apple Music UI..." -ForegroundColor Cyan
$restart = Start-Process -FilePath "python" `
    -ArgumentList "daemon.py restart" `
    -WorkingDirectory $ProjectDir `
    -RedirectStandardOutput (Join-Path $ProjectDir "flask_start.out") `
    -RedirectStandardError (Join-Path $ProjectDir "flask_start.err") `
    -NoNewWindow -Wait -PassThru
Start-Sleep -Seconds 2
$port5000 = Get-NetTCPConnection -LocalPort 5000 -State Listen -ErrorAction SilentlyContinue
if ($restart.ExitCode -eq 0 -and $port5000) {
    Write-Host "[OK] Latest UI is running on http://127.0.0.1:5000" -ForegroundColor Green
} else {
    Write-Host "[ERROR] Flask restart failed. Check: $FlaskLog" -ForegroundColor Red
    Stop-Transcript | Out-Null
    Read-Host "Press Enter to close"
    exit 1
}

# ---------- Step 4: Start cloudflared ----------
Write-Host "[2/2] Starting a fresh project cloudflared tunnel..." -ForegroundColor Cyan
$tunnelStart = Start-Process -FilePath "python" `
    -ArgumentList "scripts\start_cloudflared_detached.py" `
    -WorkingDirectory $ProjectDir `
    -RedirectStandardOutput (Join-Path $ProjectDir "cloudflared_start.out") `
    -RedirectStandardError (Join-Path $ProjectDir "cloudflared_start.err") `
    -WindowStyle Hidden -Wait -PassThru
if ($tunnelStart.ExitCode -ne 0) {
    Write-Host "[ERROR] cloudflared failed to start. Check cloudflared_start.err" -ForegroundColor Red
    Stop-Transcript | Out-Null
    Read-Host "Press Enter to close"
    exit 1
}

# ---------- Step 5: Show new public URL ----------
Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "   [Ready]" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "[Local]   http://127.0.0.1:5000" -ForegroundColor Cyan
Write-Host "[Player]  http://127.0.0.1:5000/player?ui=apple-music-v8" -ForegroundColor Magenta
Write-Host ""
Write-Host "[Public URL]" -ForegroundColor Yellow

$publicUrl = ""
if (Test-Path $LogFile) {
    $urlMatch = Select-String -Path $LogFile -Pattern "https://[a-z0-9-]+\.trycloudflare\.com" | Select-Object -Last 1
    if ($urlMatch) {
        $publicUrl = $urlMatch.Matches[0].Value
        Write-Host "    $publicUrl" -ForegroundColor Green
        # 单独存一份方便复制
        Set-Content -Path $PublicUrlFile -Value $publicUrl -Encoding UTF8
    } else {
        Write-Host "    URL not yet generated. Wait 10s and check: $LogFile" -ForegroundColor Yellow
    }
} else {
    Write-Host "    (no log file yet)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "------------------------------------------------------------" -ForegroundColor Gray

# Open the updated player with a cache-busting query parameter.
$uiVersion = [DateTimeOffset]::Now.ToUnixTimeSeconds()
Start-Process "http://127.0.0.1:5000/player?ui=apple-music-v8&v=$uiVersion"
Write-Host "[Tips]" -ForegroundColor Gray
Write-Host "  - Friend first visit: click 'Visit Site' on Cloudflare warning page"
Write-Host "  - Use browser (not WeChat built-in) on mobile"
Write-Host "  - URL changes every time cloudflared restarts"
Write-Host "  - Run MusicAnalysis-Stop.ps1 to shut down"
Write-Host "  - This window will auto-close in 30 seconds (services keep running)"
Write-Host "------------------------------------------------------------" -ForegroundColor Gray

# 写一份 transcript 日志（保留这次启动的所有输出）
Stop-Transcript | Out-Null

Write-Host ""
Write-Host "Closing in 30 seconds (Ctrl+C to close now)..." -ForegroundColor DarkGray

# 不用 ReadKey（双击 .lnk 时 ReadKey 经常拿不到输入导致闪退）
# 用 30 秒倒计时自动关闭
$timeout = 30
for ($i = $timeout; $i -gt 0; $i--) {
    Write-Host "`r  Auto-close in $i seconds...  " -NoNewline -ForegroundColor DarkGray
    Start-Sleep -Seconds 1
}
Write-Host "`r  Auto-closing now. Services keep running.            " -ForegroundColor DarkGray
exit 0
