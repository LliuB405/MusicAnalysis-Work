# Create desktop shortcuts for the maintained start/stop entry points.
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$ProjectDir = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\..")).Path
$Desktop = [Environment]::GetFolderPath("Desktop")
$Shell = New-Object -ComObject WScript.Shell

$items = @(
    @{ Name = "MusicAnalysis-Start.lnk"; Script = "MusicAnalysis-Start.ps1"; Description = "Start MusicAnalysis-Work"; Icon = "shell32.dll,12" },
    @{ Name = "MusicAnalysis-Stop.lnk"; Script = "MusicAnalysis-Stop.ps1"; Description = "Stop MusicAnalysis-Work"; Icon = "shell32.dll,27" }
)

foreach ($item in $items) {
    $shortcutPath = Join-Path $Desktop $item.Name
    $scriptPath = Join-Path $ProjectDir $item.Script
    if (-not (Test-Path -LiteralPath $scriptPath -PathType Leaf)) {
        throw "Script not found: $scriptPath"
    }
    $shortcut = $Shell.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = "powershell.exe"
    $shortcut.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`""
    $shortcut.WorkingDirectory = $ProjectDir
    $shortcut.WindowStyle = 1
    $shortcut.Description = $item.Description
    $shortcut.IconLocation = $item.Icon
    $shortcut.Save()
    Write-Host "[OK] $shortcutPath" -ForegroundColor Green
}
