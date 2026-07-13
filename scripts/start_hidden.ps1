$ErrorActionPreference = 'Stop'
$ProjectDir = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$AppScript = Join-Path $ProjectDir 'app.py'
$PythonExe = if ($env:PYTHON_EXE) {
    $env:PYTHON_EXE
} else {
    Get-Command python.exe -CommandType Application -ErrorAction SilentlyContinue |
        Select-Object -First 1 -ExpandProperty Source
}
if (-not $PythonExe) {
    throw 'python.exe was not found. Add Python to PATH or set PYTHON_EXE.'
}

$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = $PythonExe
$psi.Arguments = "`"$AppScript`""
$psi.WorkingDirectory = $ProjectDir
$psi.UseShellExecute = $true
$psi.WindowStyle = 'Hidden'
$p = [System.Diagnostics.Process]::Start($psi)
Set-Content -Path (Join-Path $ProjectDir 'flask.pid') -Value $p.Id
Write-Host "Started PID: $($p.Id)"
