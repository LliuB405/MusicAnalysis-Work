# MusicAnalysis-Work one-click launcher for Windows.
[CmdletBinding()]
param(
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
& "$env:SystemRoot\System32\chcp.com" 65001 | Out-Null
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)

$ProjectDir = $PSScriptRoot
$CloudflaredDir = Join-Path $ProjectDir "scripts\bin"
$Cloudflared = Join-Path $CloudflaredDir "cloudflared.exe"
$PublicUrlFile = Join-Path $ProjectDir "public_url.txt"

function Test-ProjectPython {
    param([Parameter(Mandatory = $true)][string]$Candidate)

    $startInfo = [System.Diagnostics.ProcessStartInfo]::new()
    $startInfo.FileName = $Candidate
    $startInfo.Arguments = '-c "import flask, requests, bs4, matplotlib, pandas, wordcloud"'
    $startInfo.UseShellExecute = $false
    $startInfo.CreateNoWindow = $true
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true

    $process = [System.Diagnostics.Process]::new()
    $process.StartInfo = $startInfo
    try {
        if (-not $process.Start()) { return $false }
        # Drain both streams asynchronously so a broken candidate cannot block
        # the launcher by filling an output pipe.
        $stdoutTask = $process.StandardOutput.ReadToEndAsync()
        $stderrTask = $process.StandardError.ReadToEndAsync()
        if (-not $process.WaitForExit(12000)) {
            try { $process.Kill() } catch { }
            return $false
        }
        $null = $stdoutTask.Result
        $null = $stderrTask.Result
        return $process.ExitCode -eq 0
    } catch {
        return $false
    } finally {
        $process.Dispose()
    }
}

function Find-ProjectPython {
    $candidates = [System.Collections.Generic.List[string]]::new()
    if ($env:MUSIC_ANALYSIS_PYTHON) { $candidates.Add($env:MUSIC_ANALYSIS_PYTHON) }
    $candidates.Add((Join-Path $ProjectDir ".venv\Scripts\python.exe"))
    $candidates.Add((Join-Path $ProjectDir ".conda\python.exe"))
    if ($env:CONDA_PREFIX) { $candidates.Add((Join-Path $env:CONDA_PREFIX "python.exe")) }
    $pathPython = Get-Command python -ErrorAction SilentlyContinue
    if ($pathPython) { $candidates.Add($pathPython.Source) }

    foreach ($candidate in $candidates | Select-Object -Unique) {
        if (-not $candidate -or -not (Test-Path -LiteralPath $candidate -PathType Leaf)) { continue }
        if (Test-ProjectPython -Candidate $candidate) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
        Write-Host "[SKIP] Python is missing required packages: $candidate" -ForegroundColor DarkYellow
    }
    throw "No usable Python was found. Run: python -m pip install -r requirements.txt"
}

Set-Location -LiteralPath $ProjectDir
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  MusicAnalysis-Work - Starting" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

try {
    $Python = Find-ProjectPython
    Write-Host "[OK] Python: $Python" -ForegroundColor Green

    $cloudflaredCandidates = @(
        $env:CLOUDFLARED_PATH,
        $Cloudflared,
        $(if (Get-Command cloudflared -ErrorAction SilentlyContinue) { (Get-Command cloudflared).Source }),
        (Join-Path $HOME ".workbuddy\binaries\cloudflared.exe")
    ) | Where-Object { $_ -and (Test-Path -LiteralPath $_ -PathType Leaf) }

    if (-not $cloudflaredCandidates) {
        Write-Host "[INFO] cloudflared is missing; downloading it now..." -ForegroundColor Yellow
        New-Item -ItemType Directory -Path $CloudflaredDir -Force | Out-Null
        Invoke-WebRequest `
            -Uri "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe" `
            -OutFile $Cloudflared `
            -UseBasicParsing
    }

    Write-Host "[1/2] Restarting Flask with the current repository UI..." -ForegroundColor Cyan
    & $Python (Join-Path $ProjectDir "daemon.py") restart
    if ($LASTEXITCODE -ne 0) { throw "Flask failed to start. Review flask.err.log." }

    Write-Host "[2/2] Creating a temporary Cloudflare public URL..." -ForegroundColor Cyan
    & $Python (Join-Path $ProjectDir "scripts\start_cloudflared_detached.py")
    if ($LASTEXITCODE -ne 0) { throw "cloudflared failed to start. Review cloudflared.log." }

    $publicUrl = if (Test-Path -LiteralPath $PublicUrlFile) {
        (Get-Content -LiteralPath $PublicUrlFile -Raw -Encoding UTF8).Trim()
    } else { "" }

    Write-Host ""
    Write-Host "[Local home]   http://127.0.0.1:5000" -ForegroundColor Green
    Write-Host "[Local player] http://127.0.0.1:5000/player" -ForegroundColor Green
    if ($publicUrl -match '^https://[a-z0-9-]+\.trycloudflare\.com$') {
        Write-Host "[Phone share]  $publicUrl" -ForegroundColor Magenta
    } else {
        Write-Host "[Phone share]  URL is not ready; review public_url.txt or cloudflared.log." -ForegroundColor Yellow
    }

    if (-not $NoBrowser) {
        Start-Process "http://127.0.0.1:5000/player"
    }
    exit 0
} catch {
    Write-Host "[ERROR] $($_.ToString())" -ForegroundColor Red
    if ($_.ScriptStackTrace) {
        Write-Host "[STACK]" -ForegroundColor Yellow
        Write-Host $_.ScriptStackTrace -ForegroundColor Yellow
    }
    if ($_.Exception.InnerException) {
        Write-Host "[INNER] $($_.Exception.InnerException.Message)" -ForegroundColor Yellow
    }
    exit 1
}
