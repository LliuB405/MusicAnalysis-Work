$psi = [System.Diagnostics.ProcessStartInfo]::new()
$psi.FileName = "cmd.exe"
$psi.Arguments = '/c "E:\Music Analysis Work\start.bat"'
$psi.WorkingDirectory = "E:\Music Analysis Work"
$psi.UseShellExecute = $false
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError = $true
$psi.CreateNoWindow = $true
$psi.StandardOutputEncoding = [System.Text.Encoding]::UTF8
$psi.StandardErrorEncoding = [System.Text.Encoding]::UTF8

$p = [System.Diagnostics.Process]::new()
$p.StartInfo = $psi

$outTask = $p.StartAsync()
$outTask.Wait()
$stdoutTask = $p.StandardOutput.ReadToEndAsync()
$stderrTask = $p.StandardError.ReadToEndAsync()
$p.WaitForExit(90000)
$stdout = $stdoutTask.Result
$stderr = $stderrTask.Result

Write-Host "Exit code: $($p.ExitCode)"
Write-Host "=== STDOUT ==="
Write-Host $stdout
Write-Host "=== STDERR ==="
Write-Host $stderr
