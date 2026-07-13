# 部署桌面快捷方式（用 .lnk 解决编码问题）
$ErrorActionPreference = "Stop"

$Desktop = [Environment]::GetFolderPath("Desktop")
$ProjectDir = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$StartScript = Join-Path $ProjectDir "MusicAnalysis-Start.ps1"
$StopScript = Join-Path $ProjectDir "MusicAnalysis-Stop.ps1"

# 1. 删旧文件
Remove-Item (Join-Path $Desktop "MusicAnalysis-*") -Force -ErrorAction SilentlyContinue

# 2. 复制 .ps1
Copy-Item $StartScript (Join-Path $Desktop "MusicAnalysis-Start.ps1") -Force
Copy-Item $StopScript (Join-Path $Desktop "MusicAnalysis-Stop.ps1") -Force

# 3. 创建快捷方式
$ws = New-Object -ComObject WScript.Shell
$s = $ws.CreateShortcut((Join-Path $Desktop "MusicAnalysis-Start.lnk"))
$s.TargetPath = "powershell.exe"
$s.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$StartScript`""
$s.WorkingDirectory = $ProjectDir
$s.WindowStyle = 1
$s.Description = "Start Music Analysis Work (Flask + Cloudflared)"
$s.IconLocation = "shell32.dll,12"  # 启动图标
$s.Save()

$s2 = $ws.CreateShortcut((Join-Path $Desktop "MusicAnalysis-Stop.lnk"))
$s2.TargetPath = "powershell.exe"
$s2.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$StopScript`""
$s2.WorkingDirectory = $ProjectDir
$s2.WindowStyle = 1
$s2.Description = "Stop Music Analysis Work"
$s2.IconLocation = "shell32.dll,27"  # 停止图标
$s2.Save()

Write-Host "[OK] Desktop shortcuts created"
Get-ChildItem (Join-Path $Desktop "MusicAnalysis-*") | Select-Object Name, Length | Format-Table
