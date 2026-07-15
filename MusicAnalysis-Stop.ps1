# MusicAnalysis-Work one-click stopper for Windows.
[CmdletBinding()]
param()

$ErrorActionPreference = "Continue"
& "$env:SystemRoot\System32\chcp.com" 65001 | Out-Null
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$ProjectDir = $PSScriptRoot
Set-Location -LiteralPath $ProjectDir

Write-Host "Stopping MusicAnalysis-Work..." -ForegroundColor Cyan

$tunnelPidFile = Join-Path $ProjectDir "cloudflared.pid"
if (Test-Path -LiteralPath $tunnelPidFile) {
    $rawPid = (Get-Content -LiteralPath $tunnelPidFile -Raw -ErrorAction SilentlyContinue).Trim()
    if ($rawPid -match '^\d+$') {
        $process = Get-Process -Id ([int]$rawPid) -ErrorAction SilentlyContinue
        if ($process -and $process.ProcessName -eq "cloudflared") {
            Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
            Write-Host "[OK] Cloudflare tunnel stopped (PID $rawPid)" -ForegroundColor Green
        }
    }
}
Remove-Item -LiteralPath $tunnelPidFile -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath (Join-Path $ProjectDir "public_url.txt") -Force -ErrorAction SilentlyContinue

$pythonCandidates = @(
    @(
        $env:MUSIC_ANALYSIS_PYTHON,
        (Join-Path $ProjectDir ".venv\Scripts\python.exe"),
        (Join-Path $ProjectDir ".conda\python.exe"),
        $(if ($env:CONDA_PREFIX) { Join-Path $env:CONDA_PREFIX "python.exe" }),
        $(if (Get-Command python -ErrorAction SilentlyContinue) { (Get-Command python).Source })
    ) | Where-Object { $_ -and (Test-Path -LiteralPath $_ -PathType Leaf) } | Select-Object -Unique
)

if ($pythonCandidates.Count -gt 0) {
    & $pythonCandidates[0] (Join-Path $ProjectDir "daemon.py") stop
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} else {
    Write-Host "[WARN] Python was not found, so daemon.py could not run. The Cloudflare tunnel is stopped." -ForegroundColor Yellow
    exit 1
}

Write-Host "[OK] All services stopped." -ForegroundColor Green
exit 0
