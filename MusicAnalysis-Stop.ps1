# Music Analysis Work - One-click Stopper (PowerShell)
$ErrorActionPreference = "Continue"
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ProjectDir = "E:\Music Analysis Work"
$OutputLog = Join-Path $ProjectDir "stop_output.log"

Set-Location $ProjectDir
Start-Transcript -Path $OutputLog -Append -Force | Out-Null

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "   Music Analysis Work  Stopping..." -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Stop cloudflared
Write-Host "[1/2] Stopping cloudflared..." -ForegroundColor Cyan
$cf = Get-Process cloudflared -ErrorAction SilentlyContinue
if ($cf) {
    Stop-Process -Name cloudflared -Force
    Start-Sleep -Seconds 1
    Write-Host "      cloudflared stopped" -ForegroundColor Green
} else {
    Write-Host "      cloudflared not running" -ForegroundColor Gray
}

# Stop Flask
Write-Host "[2/2] Stopping Flask..." -ForegroundColor Cyan
$proc = Start-Process -FilePath "python" `
    -ArgumentList "daemon.py stop" `
    -WorkingDirectory $ProjectDir `
    -RedirectStandardOutput (Join-Path $ProjectDir "flask_stop.out") `
    -RedirectStandardError (Join-Path $ProjectDir "flask_stop.err") `
    -NoNewWindow -Wait -PassThru
if ($proc.ExitCode -eq 0) {
    Write-Host "      Flask stopped" -ForegroundColor Green
} else {
    Write-Host "      Flask stop returned exit code $($proc.ExitCode)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  [Done] All services stopped. Public URL is now invalid." -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""

Stop-Transcript | Out-Null
Write-Host "Closing in 10 seconds (Ctrl+C to close now)..." -ForegroundColor DarkGray
$timeout = 10
for ($i = $timeout; $i -gt 0; $i--) {
    Write-Host "`r  Auto-close in $i seconds...  " -NoNewline -ForegroundColor DarkGray
    Start-Sleep -Seconds 1
}
exit 0
