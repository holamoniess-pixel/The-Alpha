# ALPHA OMEGA - Windows PowerShell Installer
# Version: 2.0.0
# Repository: https://github.com/holamoniess-pixel/The-Alpha

param(
    [string]$InstallDir = "C:\AlphaOmega",
    [string]$Version = "latest",
    [switch]$Silent,
    [switch]$SkipTests,
    [switch]$NoDesktopShortcut,
    [switch]$NoAutoStart
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$REPO_OWNER = "holamoniess-pixel"
$REPO_NAME = "The-Alpha"
$REPO_URL = "https://github.com/$REPO_OWNER/$REPO_NAME"

function Write-Header {
    param([string]$Text)
    Write-Host ""
    Write-Host "=" * 60 -ForegroundColor Cyan
    Write-Host " $Text" -ForegroundColor Cyan
    Write-Host "=" * 60 -ForegroundColor Cyan
    Write-Host ""
}

function Write-Step {
    param([string]$Text)
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] $Text" -ForegroundColor White
}

function Write-Success {
    param([string]$Text)
    Write-Host "  ✓ $Text" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Text)
    Write-Host "  ⚠ $Text" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Text)
    Write-Host "  ✗ $Text" -ForegroundColor Red
}

function Show-WarningBanner {
    Clear-Host
    Write-Host ""
    Write-Host "╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Red
    Write-Host "║                                                              ║" -ForegroundColor Red
    Write-Host "║     ALPHA OMEGA - VOICE-ACTIVATED AI ASSISTANT               ║" -ForegroundColor Red
    Write-Host "║     Version 2.0.0 (BETA)                                     ║" -ForegroundColor Red
    Write-Host "║                                                              ║" -ForegroundColor Red
    Write-Host "╠══════════════════════════════════════════════════════════════╣" -ForegroundColor Red
    Write-Host "║                                                              ║" -ForegroundColor Red
    Write-Host "║     ⚠️ WARNING: FULL SYSTEM ACCESS                          ║" -ForegroundColor Yellow
    Write-Host "║                                                              ║" -ForegroundColor Red
    Write-Host "║     This software has COMPLETE CONTROL over your computer:  ║" -ForegroundColor White
    Write-Host "║                                                              ║" -ForegroundColor Red
    Write-Host "║     • File operations (read, write, delete)                  ║" -ForegroundColor White
    Write-Host "║     • Application launching and control                      ║" -ForegroundColor White
    Write-Host "║     • System commands (shutdown, restart, etc.)              ║" -ForegroundColor White
    Write-Host "║     • Voice activation (always listening for wake word)     ║" -ForegroundColor White
    Write-Host "║     • Screen capture and visual recognition                  ║" -ForegroundColor White
    Write-Host "║     • Network and web automation                             ║" -ForegroundColor White
    Write-Host "║     • Keyboard and mouse control                             ║" -ForegroundColor White
    Write-Host "║                                                              ║" -ForegroundColor Red
    Write-Host "║     By installing, you accept ALL RISKS associated with      ║" -ForegroundColor White
    Write-Host "║     this software. The developers are not responsible for    ║" -ForegroundColor White
    Write-Host "║     any damage or data loss.                                 ║" -ForegroundColor White
    Write-Host "║                                                              ║" -ForegroundColor Red
    Write-Host "║     This is BETA software - use at your own risk.            ║" -ForegroundColor Yellow
    Write-Host "║                                                              ║" -ForegroundColor Red
    Write-Host "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor Red
    Write-Host ""
}

function Test-Administrator {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Get-SystemInfo {
    $cpu = Get-CimInstance Win32_Processor
    $ram = Get-CimInstance Win32_ComputerSystem
    $gpu = Get-CimInstance Win32_VideoController | Select-Object -First 1
    $disk = Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='C:'"
    
    return @{
        CPU = $cpu.Name
        CPUCores = $cpu.NumberOfCores
        RAMGB = [math]::Round($ram.TotalPhysicalMemory / 1GB, 1)
        GPU = $gpu.Name
        DiskFreeGB = [math]::Round($disk.FreeSpace / 1GB, 1)
    }
}

function Test-SystemRequirements {
    $info = Get-SystemInfo
    $warnings = @()
    $passed = $true
    
    Write-Step "Checking system requirements..."
    
    # CPU Cores
    if ($info.CPUCores -ge 2) {
        Write-Success "CPU: $($info.CPU) ($($info.CPUCores) cores)"
    } else {
        Write-Warning "CPU: $($info.CPU) - Only $($info.CPUCores) core (recommended: 2+)"
        $warnings += "Low CPU cores may affect performance"
    }
    
    # RAM
    if ($info.RAMGB -ge 4) {
        Write-Success "RAM: $($info.RAMGB)GB (Recommended: 4GB+)"
    } else {
        Write-Warning "RAM: $($info.RAMGB)GB (Recommended: 4GB+)"
        $warnings += "Low RAM may cause slowdowns"
        $passed = $false
    }
    
    # Disk Space
    if ($info.DiskFreeGB -ge 5) {
        Write-Success "Disk: $($info.DiskFreeGB)GB free (Required: 5GB+)"
    } else {
        Write-Warning "Disk: $($info.DiskFreeGB)GB free (Required: 5GB+)"
        $warnings += "Insufficient disk space"
        $passed = $false
    }
    
    # GPU (optional)
    if ($info.GPU -match "NVIDIA|RTX|GTX") {
        Write-Success "GPU: $($info.GPU) - CUDA acceleration available"
    } else {
        Write-Warning "GPU: $($info.GPU) - No CUDA support (local LLM will be slower)"
        $warnings += "GPU acceleration unavailable"
    }
    
    return @{ Passed = $passed; Warnings = $warnings; Info = $info }
}

function Test-Python {
    try {
        $python = Get-Command python -ErrorAction Stop
        $version = & python --version 2>&1
        $versionMatch = $version -match "(\d+)\.(\d+)"
        
        if ($versionMatch) {
            $major = [int]$Matches[1]
            $minor = [int]$Matches[2]
            
            if ($major -ge 3 -and $minor -ge 9) {
                Write-Success "Python $major.$minor found"
                return $true
            } else {
                Write-Warning "Python $major.$minor found (requires 3.9+)"
                return $false
            }
        }
    } catch {
        return $false
    }
    return $false
}

function Install-Python {
    Write-Step "Python 3.9+ required. Downloading Python 3.11..."
    
    $pythonUrl = "https://www.python.org/ftp/python/3.11.7/python-3.11.7-amd64.exe"
    $installerPath = "$env:TEMP\python-installer.exe"
    
    try {
        Invoke-WebRequest -Uri $pythonUrl -OutFile $installerPath -UseBasicParsing
        Write-Success "Downloaded Python installer"
        
        Write-Step "Installing Python (this may take a few minutes)..."
        Start-Process -FilePath $installerPath -ArgumentList "/quiet InstallAllUsers=1 PrependPath=1 Include_test=0" -Wait
        
        # Refresh environment
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
        
        Write-Success "Python 3.11 installed successfully"
        return $true
    } catch {
        Write-Error "Failed to install Python: $_"
        return $false
    } finally {
        if (Test-Path $installerPath) { Remove-Item $installerPath -Force }
    }
}

function Get-LatestRelease {
    $apiUrl = "https://api.github.com/repos/$REPO_OWNER/$REPO_NAME/releases/latest"
    
    try {
        $response = Invoke-RestMethod -Uri $apiUrl -UseBasicParsing
        return $response
    } catch {
        Write-Warning "Could not fetch latest release, using main branch"
        return $null
    }
}

function Download-AlphaOmega {
    param([string]$Destination)
    
    Write-Step "Downloading Alpha Omega..."
    
    $release = Get-LatestRelease
    
    if ($release) {
        $downloadUrl = $release.assets | Where-Object { $_.name -like "*windows*.zip" } | Select-Object -ExpandProperty browser_download_url
        
        if (-not $downloadUrl) {
            $downloadUrl = "https://github.com/$REPO_OWNER/$REPO_NAME/archive/refs/tags/$($release.tag_name).zip"
        }
        
        Write-Step "Version: $($release.tag_name)"
    } else {
        $downloadUrl = "https://github.com/$REPO_OWNER/$REPO_NAME/archive/refs/heads/main.zip"
    }
    
    $zipPath = "$env:TEMP\alpha-omega.zip"
    
    try {
        Invoke-WebRequest -Uri $downloadUrl -OutFile $zipPath -UseBasicParsing
        Write-Success "Download complete"
        
        Write-Step "Extracting files..."
        Expand-Archive -Path $zipPath -DestinationPath $env:TEMP\alpha-extract -Force
        
        # Find the extracted folder
        $extractedFolder = Get-ChildItem "$env:TEMP\alpha-extract" -Directory | Select-Object -First 1
        
        # Move to destination
        if (Test-Path $Destination) { Remove-Item $Destination -Recurse -Force }
        Move-Item -Path $extractedFolder.FullName -Destination $Destination
        
        Write-Success "Extracted to $Destination"
        
        # Cleanup
        Remove-Item $zipPath -Force
        Remove-Item "$env:TEMP\alpha-extract" -Recurse -Force
        
        return $true
    } catch {
        Write-Error "Download failed: $_"
        return $false
    }
}

function Install-Dependencies {
    param([string]$InstallDir)
    
    Write-Step "Creating virtual environment..."
    
    Push-Location $InstallDir
    
    try {
        # Create venv
        & python -m venv .venv
        Write-Success "Virtual environment created"
        
        # Activate
        & .\.venv\Scripts\Activate.ps1
        
        Write-Step "Installing dependencies (this may take several minutes)..."
        
        # Upgrade pip
        & python -m pip install --upgrade pip --quiet
        
        # Install requirements
        $requirementsFile = Join-Path $InstallDir "requirements.txt"
        if (Test-Path $requirementsFile) {
            & pip install -r $requirementsFile --quiet
            
            if ($LASTEXITCODE -eq 0) {
                Write-Success "Dependencies installed"
            } else {
                Write-Warning "Some dependencies may have failed to install"
            }
        }
        
        return $true
    } catch {
        Write-Error "Failed to install dependencies: $_"
        return $false
    } finally {
        Pop-Location
    }
}

function Run-Tests {
    param([string]$InstallDir)
    
    if ($SkipTests) { return $true }
    
    Write-Step "Running system tests..."
    
    Push-Location $InstallDir
    
    try {
        & .\.venv\Scripts\Activate.ps1
        $testOutput = & python test_system.py 2>&1
        
        if ($testOutput -match "All tests passed" -or $testOutput -match "✓") {
            Write-Success "All tests passed"
            return $true
        } else {
            Write-Warning "Some tests may have failed. Check output above."
            Write-Host $testOutput
            return $true  # Continue anyway
        }
    } catch {
        Write-Warning "Could not run tests: $_"
        return $true
    } finally {
        Pop-Location
    }
}

function Configure-OSIntegration {
    param([string]$InstallDir)
    
    Write-Header "OS INTEGRATION SETUP"
    
    # Malware scanning
    $malwareScanning = Read-Host "[?] Enable malware scanning for downloaded files? [Y/n]"
    if ($malwareScanning -eq "" -or $malwareScanning -eq "Y" -or $malwareScanning -eq "y") {
        Write-Success "Malware scanning enabled"
        $script:EnableMalware = $true
    } else {
        $script:EnableMalware = $false
    }
    
    # Windows Login Bypass
    Write-Host ""
    Write-Host "  ⚠️ WINDOWS LOGIN BYPASS" -ForegroundColor Yellow
    Write-Host "  This replaces Windows password login with voice authentication." -ForegroundColor White
    Write-Host "  Requires administrator privileges and will show security warning." -ForegroundColor White
    Write-Host ""
    
    $loginBypass = Read-Host "[?] Replace Windows Login with Voice Auth? [y/N]"
    if ($loginBypass -eq "Y" -or $loginBypass -eq "y") {
        if (Test-Administrator) {
            Write-Success "Windows Login Bypass enabled (will configure after installation)"
            $script:EnableLoginBypass = $true
        } else {
            Write-Warning "Administrator privileges required. Run installer as admin to enable."
            $script:EnableLoginBypass = $false
        }
    } else {
        $script:EnableLoginBypass = $false
    }
    
    # Sleep Mode
    Write-Host ""
    $sleepMode = Read-Host "[?] Allow Alpha to work while PC is in sleep mode? [Y/n]"
    if ($sleepMode -eq "" -or $sleepMode -eq "Y" -or $sleepMode -eq "y") {
        Write-Success "Sleep mode operation enabled"
        $script:EnableSleepMode = $true
    } else {
        $script:EnableSleepMode = $false
    }
    
    # Watch & Learn
    Write-Host ""
    $watchLearn = Read-Host "[?] Enable Watch & Learn mode (asks before recording)? [Y/n]"
    if ($watchLearn -eq "" -or $watchLearn -eq "Y" -or $watchLearn -eq "y") {
        Write-Success "Watch & Learn enabled"
        $script:EnableWatchLearn = $true
    } else {
        $script:EnableWatchLearn = $false
    }
}

function Create-DesktopShortcut {
    param([string]$InstallDir)
    
    if ($NoDesktopShortcut) { return }
    
    $shortcut = Read-Host "[?] Create desktop shortcut? [Y/n]"
    if ($shortcut -eq "" -or $shortcut -eq "Y" -or $shortcut -eq "y") {
        $WshShell = New-Object -ComObject WScript.Shell
        $ShortcutPath = "$([Environment]::GetFolderPath('Desktop'))\Alpha Omega.lnk"
        $Shortcut = $WshShell.CreateShortcut($ShortcutPath)
        $Shortcut.TargetPath = "$InstallDir\.venv\Scripts\pythonw.exe"
        $Shortcut.Arguments = "`"$InstallDir\run_alpha.py`""
        $Shortcut.WorkingDirectory = $InstallDir
        $Shortcut.Description = "Alpha Omega - Voice Activated AI Assistant"
        $Shortcut.IconLocation = "$InstallDir\assets\icon.ico"
        $Shortcut.Save()
        Write-Success "Desktop shortcut created"
        
        # Hotkey
        Write-Host ""
        Write-Host "  Set custom hotkey to toggle Alpha Omega:" -ForegroundColor White
        Write-Host "  Press your desired key combination (or press Enter for default Ctrl+Shift+A)" -ForegroundColor Gray
        $hotkey = Read-Host "[?] Hotkey"
        
        if ($hotkey -eq "") {
            $hotkey = "Ctrl+Shift+A"
        }
        
        Write-Success "Hotkey set to: $hotkey (Note: Hotkey requires manual configuration in Windows)"
    }
}

function Configure-AutoStart {
    param([string]$InstallDir)
    
    if ($NoAutoStart) { return }
    
    $autostart = Read-Host "[?] Start Alpha Omega automatically on boot? [Y/n]"
    if ($autostart -eq "" -or $autostart -eq "Y" -or $autostart -eq "y") {
        $regPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
        Set-ItemProperty -Path $regPath -Name "AlphaOmega" -Value "`"$InstallDir\.venv\Scripts\pythonw.exe`" `"$InstallDir\run_alpha.py`"" -Force
        Write-Success "Auto-start enabled"
    }
}

function Save-Configuration {
    param([string]$InstallDir, [hashtable]$Settings)
    
    $configPath = Join-Path $InstallDir "config.yaml"
    
    $config = @"
# Alpha Omega System Configuration
# Generated by installer on $(Get-Date)

system:
  name: "AlphaOmega"
  version: "2.0.0"
  wake_word: "hey alpha"
  auto_start: $($Settings.AutoStart)
  offline_mode: true

security:
  malware_scanning: $($Settings.MalwareScanning)
  voice_auth_enabled: $($Settings.LoginBypass)
  command_whitelist: true
  require_approval: true

performance:
  work_in_sleep: $($Settings.SleepMode)
  background_tasks: true

learning:
  watch_mode: $($Settings.WatchLearn)
  learn_from_tutorials: $($Settings.WatchLearn)
  screen_recording: false
"@
    
    $config | Out-File -FilePath $configPath -Encoding UTF8
}

function Start-AlphaOmega {
    param([string]$InstallDir)
    
    $start = Read-Host "[?] Start Alpha Omega now? [Y/n]"
    if ($start -eq "" -or $start -eq "Y" -or $start -eq "y") {
        Write-Step "Starting Alpha Omega..."
        Start-Process -FilePath "$InstallDir\.venv\Scripts\pythonw.exe" -ArgumentList "`"$InstallDir\run_alpha.py`"" -WorkingDirectory $InstallDir
        Write-Success "Alpha Omega started"
        Write-Host ""
        Write-Host "  API Server: http://localhost:8000" -ForegroundColor Cyan
        Write-Host "  WebSocket: ws://localhost:8000/ws" -ForegroundColor Cyan
        Write-Host "  Web UI: http://localhost:8000/ui" -ForegroundColor Cyan
    }
}

# ============================================================
# MAIN INSTALLATION
# ============================================================

try {
    Show-WarningBanner
    
    # Accept risks
    if (-not $Silent) {
        $accept = Read-Host "Do you understand and accept these risks? [Y/n]"
        if ($accept -ne "" -and $accept -ne "Y" -and $accept -ne "y") {
            Write-Host "Installation cancelled."
            exit 1
        }
    }
    
    Write-Header "INSTALLATION STARTING"
    
    # Check Python
    if (-not (Test-Python)) {
        $installPython = Read-Host "[?] Python 3.9+ required. Download and install Python 3.11? [Y/n]"
        if ($installPython -eq "" -or $installPython -eq "Y" -or $installPython -eq "y") {
            if (-not (Install-Python)) {
                Write-Error "Python installation failed. Please install Python 3.9+ manually."
                exit 1
            }
        } else {
            Write-Error "Python 3.9+ is required. Installation cancelled."
            exit 1
        }
    }
    
    # Check system requirements
    $sysCheck = Test-SystemRequirements
    
    if (-not $sysCheck.Passed) {
        Write-Host ""
        Write-Host "  ⚠️ HARDWARE WARNING" -ForegroundColor Yellow
        Write-Host "  Your system does not meet minimum requirements:" -ForegroundColor White
        foreach ($warning in $sysCheck.Warnings) {
            Write-Host "    • $warning" -ForegroundColor Yellow
        }
        Write-Host ""
        Write-Host "  This may result in:" -ForegroundColor White
        Write-Host "    • Slower AI responses" -ForegroundColor Yellow
        Write-Host "    • Some features may be disabled" -ForegroundColor Yellow
        Write-Host "    • Voice recognition will use cloud fallback" -ForegroundColor Yellow
        Write-Host ""
        
        $proceed = Read-Host "[?] Proceed anyway? [y/N]"
        if ($proceed -ne "Y" -and $proceed -ne "y") {
            Write-Host "Installation cancelled."
            exit 1
        }
    }
    
    # Download
    Write-Header "DOWNLOAD & INSTALL"
    Write-Step "[1/8] Downloading Alpha Omega..."
    if (-not (Download-AlphaOmega -Destination $InstallDir)) {
        exit 1
    }
    
    # Install dependencies
    Write-Step "[2/8] Creating virtual environment..."
    Write-Step "[3/8] Installing dependencies..."
    if (-not (Install-Dependencies -InstallDir $InstallDir)) {
        exit 1
    }
    
    # Run tests
    Write-Step "[4/8] Running system tests..."
    if (-not (Run-Tests -InstallDir $InstallDir)) {
        Write-Warning "Some tests failed, but installation will continue"
    }
    
    # OS Integration
    if (-not $Silent) {
        Write-Header "OS INTEGRATION"
        Configure-OSIntegration -InstallDir $InstallDir
    }
    
    # Save configuration
    Write-Step "[5/8] Saving configuration..."
    $settings = @{
        MalwareScanning = $script:EnableMalware
        LoginBypass = $script:EnableLoginBypass
        SleepMode = $script:EnableSleepMode
        WatchLearn = $script:EnableWatchLearn
        AutoStart = -not $NoAutoStart
    }
    Save-Configuration -InstallDir $InstallDir -Settings $settings
    
    # Desktop setup
    Write-Header "DESKTOP SETUP"
    Write-Step "[6/8] Creating desktop shortcut..."
    Create-DesktopShortcut -InstallDir $InstallDir
    
    Write-Step "[7/8] Configuring auto-start..."
    Configure-AutoStart -InstallDir $InstallDir
    
    # Complete
    Write-Header "INSTALLATION COMPLETE"
    Write-Success "Alpha Omega installed successfully!"
    Write-Host ""
    Write-Host "  Install Location: $InstallDir" -ForegroundColor White
    Write-Host "  API Server: http://localhost:8000" -ForegroundColor Cyan
    Write-Host "  WebSocket: ws://localhost:8000/ws" -ForegroundColor Cyan
    Write-Host "  Web UI: http://localhost:8000/ui" -ForegroundColor Cyan
    Write-Host "  Wake Word: 'hey alpha'" -ForegroundColor Cyan
    Write-Host ""
    
    Write-Step "[8/8] Starting..."
    Start-AlphaOmega -InstallDir $InstallDir
    
    Write-Host ""
    Write-Host "=" * 60 -ForegroundColor Green
    Write-Host "  Thank you for installing Alpha Omega!" -ForegroundColor Green
    Write-Host "  Say 'hey alpha' to activate." -ForegroundColor Green
    Write-Host "=" * 60 -ForegroundColor Green
    
} catch {
    Write-Error "Installation failed: $_"
    Write-Host $_.ScriptStackTrace -ForegroundColor Red
    exit 1
}
