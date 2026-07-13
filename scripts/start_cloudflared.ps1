$ErrorActionPreference = 'Stop'
$ProjectDir = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$CloudflaredExe = if ($env:CLOUDFLARED_EXE) {
    $env:CLOUDFLARED_EXE
} else {
    Get-Command cloudflared.exe -CommandType Application -ErrorAction SilentlyContinue |
        Select-Object -First 1 -ExpandProperty Source
}
if (-not $CloudflaredExe) {
    throw 'cloudflared.exe was not found. Add it to PATH or set CLOUDFLARED_EXE.'
}

$ps = New-Object System.Diagnostics.ProcessStartInfo
$ps.FileName = $CloudflaredExe
$ps.Arguments = 'tunnel --url http://127.0.0.1:5000 --no-autoupdate'
$ps.WorkingDirectory = $ProjectDir
$ps.UseShellExecute = $false
$ps.RedirectStandardOutput = $true
$ps.RedirectStandardError = $true
$ps.CreateNoWindow = $true
$p = [System.Diagnostics.Process]::Start($ps)
Set-Content -Path (Join-Path $ProjectDir 'cloudflared.pid') -Value $p.Id
Write-Host "Started cloudflared PID: $($p.Id)"
