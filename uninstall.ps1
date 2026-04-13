# ALPHA OMEGA - Windows Uninstaller
# Run: iwr -useb https://raw.githubusercontent.com/YOUR_USERNAME/alpha/main/uninstall.ps1 | iex

param([switch]$KeepData)

$InstallDir = "C:\AlphaOmega"
$ErrorActionPreference = "Stop"

Write-Host "ALPHA OMEGA UNINSTALLER" -ForegroundColor Cyan
Write-Host "========================" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path $InstallDir)) {
    Write-Host "Alpha Omega is not installed." -ForegroundColor Yellow
    exit 0
}

# Ask about data
$keepData = $KeepData
if (-not $keepData) {
    $keepData = Read-Host "Keep user data and logs? [y/N]"
    $keepData = ($keepData -eq "Y" -or $keepData -eq "y")
}

# Stop running processes
Write-Host "Stopping processes..." -ForegroundColor White
Get-Process -Name python* -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 2

# Remove auto-start
Write-Host "Removing auto-start..." -ForegroundColor White
Remove-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name "AlphaOmega" -ErrorAction SilentlyContinue

# Remove desktop shortcut
Write-Host "Removing shortcuts..." -ForegroundColor White
Remove-Item "$([Environment]::GetFolderPath('Desktop'))\Alpha Omega.lnk" -ErrorAction SilentlyContinue
Remove-Item "$([Environment]::GetFolderPath('StartMenu'))\Programs\Alpha Omega.lnk" -ErrorAction SilentlyContinue

# Remove files
Write-Host "Removing files..." -ForegroundColor White
if ($keepData) {
    # Keep data folder
    $folders = @("src", "apps", ".venv", "assets", "web", "plugins")
    foreach ($folder in $folders) {
        $path = Join-Path $InstallDir $folder
        if (Test-Path $path) { Remove-Item $path -Recurse -Force }
    }
    Remove-Item "$InstallDir\*.py" -Force
    Remove-Item "$InstallDir\*.bat" -Force
    Write-Host "Data preserved at: $InstallDir\data" -ForegroundColor Green
} else {
    Remove-Item $InstallDir -Recurse -Force
    Write-Host "All files removed" -ForegroundColor Green
}

Write-Host ""
Write-Host "✓ Alpha Omega uninstalled successfully" -ForegroundColor Green
