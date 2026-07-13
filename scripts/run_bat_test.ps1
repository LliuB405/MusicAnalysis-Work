$env:PYTHONUNBUFFERED = "1"
$ProjectDir = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $ProjectDir
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# 用 Start-Process -Wait -NoNewWindow 模拟"双击 .bat"
# 但在 stdout 抓取完整输出
$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = "cmd.exe"
$psi.Arguments = "/c start_simple.bat"
$psi.WorkingDirectory = $ProjectDir
$psi.UseShellExecute = $false
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError = $true
$psi.CreateNoWindow = $false

$p = [System.Diagnostics.Process]::Start($psi)
$stdout = $p.StandardOutput.ReadToEndAsync()
$stderr = $p.StandardError.ReadToEndAsync()
$p.WaitForExit()

Write-Host "===== STDOUT ====="
Write-Host $stdout.Result
Write-Host "===== STDERR ====="
Write-Host $stderr.Result
Write-Host "===== EXIT CODE: $($p.ExitCode) ====="
