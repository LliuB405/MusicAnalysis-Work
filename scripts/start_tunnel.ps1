$ErrorActionPreference = 'Stop'
$ProjectDir = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$TunnelScript = Join-Path $ProjectDir 'lt_client.py'
$PythonExe = if ($env:PYTHON_EXE) {
    $env:PYTHON_EXE
} else {
    Get-Command python.exe -CommandType Application -ErrorAction SilentlyContinue |
        Select-Object -First 1 -ExpandProperty Source
}
if (-not $PythonExe) {
    throw 'python.exe was not found. Add Python to PATH or set PYTHON_EXE.'
}

$ps = New-Object System.Diagnostics.ProcessStartInfo
$ps.FileName = $PythonExe
$ps.Arguments = "`"$TunnelScript`" 5000"
$ps.WorkingDirectory = $ProjectDir
$ps.UseShellExecute = $false
$ps.RedirectStandardOutput = $true
$ps.RedirectStandardError = $true
$ps.CreateNoWindow = $true
$p = [System.Diagnostics.Process]::Start($ps)
Set-Content -Path (Join-Path $ProjectDir 'lt_client.pid') -Value $p.Id
Write-Host "Started tunnel client PID: $($p.Id)"
