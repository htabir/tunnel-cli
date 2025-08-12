# Tunnel CLI Installer for Windows
# Usage: irm https://tunnel.ovream.com/install.ps1 | iex
# or: Invoke-WebRequest -Uri https://tunnel.ovream.com/install.ps1 | Invoke-Expression

$ErrorActionPreference = "Stop"

# Configuration
$GITHUB_REPO = "htabir/tunnel-cli"
$INSTALL_DIR = "$env:USERPROFILE\.tunnel-cli"

# Functions
function Write-Banner {
    Write-Host ""
    Write-Host "╔══════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║   Tunnel CLI Installer for Windows   ║" -ForegroundColor Cyan
    Write-Host "║       tunnel.ovream.com              ║" -ForegroundColor Cyan
    Write-Host "╚══════════════════════════════════════╝" -ForegroundColor Cyan
    Write-Host ""
}

function Write-Success {
    param([string]$Message)
    Write-Host "✓ " -ForegroundColor Green -NoNewline
    Write-Host $Message
}

function Write-Error {
    param([string]$Message)
    Write-Host "✗ " -ForegroundColor Red -NoNewline
    Write-Host $Message
}

function Write-Info {
    param([string]$Message)
    Write-Host "ℹ " -ForegroundColor Blue -NoNewline
    Write-Host $Message
}

function Write-Warning {
    param([string]$Message)
    Write-Host "⚠ " -ForegroundColor Yellow -NoNewline
    Write-Host $Message
}

# Check Python installation
function Test-PythonInstallation {
    $pythonCmd = $null
    $pythonInfo = $null
    
    # Try different Python commands
    $commands = @("python", "python3", "py")
    
    foreach ($cmd in $commands) {
        try {
            $version = & $cmd --version 2>&1
            if ($version -match "Python (\d+)\.(\d+)") {
                $major = [int]$matches[1]
                $minor = [int]$matches[2]
                
                if ($major -eq 3 -and $minor -ge 8) {
                    $pythonCmd = $cmd
                    $pythonInfo = $version
                    Write-Success "Found $version ($cmd)"
                    break
                }
            }
        } catch {
            # Command not found, continue
        }
    }
    
    if ($null -eq $pythonCmd) {
        Write-Error "Python 3.8+ not found"
        Write-Host ""
        Write-Info "Please install Python from:"
        Write-Host "  https://www.python.org/downloads/" -ForegroundColor Cyan
        Write-Host ""
        Write-Warning "During installation, make sure to:"
        Write-Host "  1. Check 'Add Python to PATH'" -ForegroundColor White
        Write-Host "  2. Check 'Install pip'" -ForegroundColor White
        Write-Host ""
        Write-Host "After installing Python, run this installer again." -ForegroundColor Yellow
        exit 1
    }
    
    return $pythonCmd
}

# Install dependencies
function Install-Dependencies {
    param([string]$PythonCmd)
    
    Write-Info "Installing dependencies..."
    
    # Upgrade pip
    & $PythonCmd -m pip install --user --upgrade pip --quiet 2>$null
    
    # Install required packages
    & $PythonCmd -m pip install --user --upgrade `
        textual `
        aiohttp `
        requests `
        python-dotenv --quiet 2>$null
    
    Write-Success "Dependencies installed"
}

# Download and install CLI
function Install-TunnelCLI {
    param([string]$PythonCmd)
    
    Write-Info "Downloading Tunnel CLI..."
    
    # Create temp directory
    $tempDir = New-TemporaryFile | %{ Remove-Item $_; New-Item -ItemType Directory -Path $_ }
    Push-Location $tempDir
    
    try {
        # Download from GitHub
        $downloadUrl = "https://github.com/$GITHUB_REPO/archive/refs/heads/main.zip"
        $zipFile = Join-Path $tempDir "tunnel-cli.zip"
        
        # Download the file
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        Invoke-WebRequest -Uri $downloadUrl -OutFile $zipFile -UseBasicParsing
        
        Write-Info "Extracting files..."
        Expand-Archive -Path $zipFile -DestinationPath $tempDir -Force
        
        # Navigate to extracted directory
        Set-Location (Join-Path $tempDir "tunnel-cli-main")
        
        Write-Info "Installing Tunnel CLI..."
        & $PythonCmd -m pip install --user . --quiet
        
        Write-Success "Tunnel CLI installed"
    }
    catch {
        Write-Error "Installation failed: $_"
        exit 1
    }
    finally {
        # Cleanup
        Pop-Location
        Remove-Item -Path $tempDir -Recurse -Force -ErrorAction SilentlyContinue
    }
}

# Create launcher scripts
function Create-Launchers {
    param([string]$PythonCmd)
    
    Write-Info "Creating launcher scripts..."
    
    # Create Scripts directory if it doesn't exist
    $scriptsDir = Join-Path $env:USERPROFILE "Scripts"
    if (!(Test-Path $scriptsDir)) {
        New-Item -ItemType Directory -Path $scriptsDir -Force | Out-Null
    }
    
    # Create batch file for Command Prompt
    $batchFile = Join-Path $scriptsDir "tunnel.bat"
    $batchContent = "@echo off`n$PythonCmd -m tunnel_cli %*"
    Set-Content -Path $batchFile -Value $batchContent -Force
    Write-Success "Created batch launcher: $batchFile"
    
    # Create PowerShell script
    $psScriptFile = Join-Path $scriptsDir "tunnel.ps1"
    $psScriptContent = "& $PythonCmd -m tunnel_cli `$args"
    Set-Content -Path $psScriptFile -Value $psScriptContent -Force
    Write-Success "Created PowerShell launcher: $psScriptFile"
    
    # Also create one in user profile for backwards compatibility
    $profileBatch = Join-Path $env:USERPROFILE "tunnel.bat"
    Copy-Item $batchFile $profileBatch -Force
    
    # Create PowerShell function/alias in all PowerShell profiles
    $profiles = @(
        $PROFILE.CurrentUserCurrentHost,
        $PROFILE.CurrentUserAllHosts
    )
    
    $aliasCommand = @"

# Tunnel CLI alias (added by installer)
function tunnel { & $PythonCmd -m tunnel_cli `$args }
Set-Alias -Name tnl -Value tunnel -Scope Global -ErrorAction SilentlyContinue
"@
    
    foreach ($profilePath in $profiles) {
        if ($profilePath) {
            $psProfileDir = Split-Path $profilePath -Parent
            if (!(Test-Path $psProfileDir)) {
                New-Item -ItemType Directory -Path $psProfileDir -Force | Out-Null
            }
            
            if (Test-Path $profilePath) {
                $profileContent = Get-Content $profilePath -Raw -ErrorAction SilentlyContinue
                if ($profileContent -and ($profileContent -notmatch "function tunnel")) {
                    Add-Content -Path $profilePath -Value $aliasCommand
                    Write-Success "Added tunnel alias to $profilePath"
                }
            } else {
                Set-Content -Path $profilePath -Value $aliasCommand
                Write-Success "Created PowerShell profile with tunnel alias: $profilePath"
            }
        }
    }
    
    # Create a tunnel.cmd file for broader compatibility
    $cmdFile = Join-Path $scriptsDir "tunnel.cmd"
    $cmdContent = "@echo off`n$PythonCmd -m tunnel_cli %*"
    Set-Content -Path $cmdFile -Value $cmdContent -Force
    Write-Success "Created CMD launcher: $cmdFile"
}

# Update PATH
function Update-Path {
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    $scriptsDir = Join-Path $env:USERPROFILE "Scripts"
    $userProfile = $env:USERPROFILE
    
    $pathsToAdd = @($scriptsDir, $userProfile)
    $pathsAdded = @()
    
    foreach ($pathToAdd in $pathsToAdd) {
        if ($userPath -notlike "*$pathToAdd*") {
            $userPath = "$userPath;$pathToAdd"
            $pathsAdded += $pathToAdd
        }
    }
    
    if ($pathsAdded.Count -gt 0) {
        [Environment]::SetEnvironmentVariable("Path", $userPath, "User")
        $env:Path = "$env:Path;$($pathsAdded -join ';')"
        foreach ($added in $pathsAdded) {
            Write-Success "Added $added to PATH"
        }
    } else {
        Write-Info "PATH already includes all required directories"
    }
}

# Test installation
function Test-Installation {
    param([string]$PythonCmd)
    
    Write-Info "Testing installation..."
    
    try {
        $output = & $PythonCmd -m tunnel_cli --help 2>&1
        if ($output -match "Tunnel CLI") {
            Write-Success "Installation test passed"
            return $true
        }
    } catch {
        Write-Warning "Installation test failed"
        return $false
    }
    
    return $false
}

# Main installation flow
function Install-Main {
    Write-Banner
    
    Write-Host "Starting installation..." -ForegroundColor White -BackgroundColor DarkBlue
    Write-Host ""
    
    # Check Python
    $pythonCmd = Test-PythonInstallation
    
    # Install dependencies
    Install-Dependencies -PythonCmd $pythonCmd
    
    # Install CLI
    Install-TunnelCLI -PythonCmd $pythonCmd
    
    # Create launchers
    Create-Launchers -PythonCmd $pythonCmd
    
    # Update PATH
    Update-Path
    
    # Test installation
    $testResult = Test-Installation -PythonCmd $pythonCmd
    
    Write-Host ""
    Write-Host "╔══════════════════════════════════════╗" -ForegroundColor Green
    Write-Host "║   Installation Complete! 🎉          ║" -ForegroundColor Green
    Write-Host "╚══════════════════════════════════════╝" -ForegroundColor Green
    Write-Host ""
    Write-Host "The 'tunnel' command has been installed!" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "You can now use it in:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  ✓ PowerShell:    " -ForegroundColor Green -NoNewline
    Write-Host "tunnel"
    Write-Host "  ✓ Command Prompt: " -ForegroundColor Green -NoNewline
    Write-Host "tunnel"
    Write-Host "  ✓ Windows Terminal: " -ForegroundColor Green -NoNewline
    Write-Host "tunnel"
    Write-Host ""
    Write-Host "Available immediately:" -ForegroundColor Yellow
    Write-Host "  $pythonCmd -m tunnel_cli" -ForegroundColor Green
    Write-Host ""
    Write-Host "After restarting your terminal:" -ForegroundColor Yellow
    Write-Host "  tunnel              - Start the TUI" -ForegroundColor Green
    Write-Host "  tunnel --help       - Show help" -ForegroundColor Green
    Write-Host "  tunnel --version    - Show version" -ForegroundColor Green
    Write-Host "  tnl                 - Short alias (PowerShell only)" -ForegroundColor Green
    Write-Host ""
    Write-Host "Portal: " -ForegroundColor Gray -NoNewline
    Write-Host "https://tunnel.ovream.com" -ForegroundColor Cyan
    Write-Host ""
    
    if (-not $testResult) {
        Write-Warning "Installation completed with warnings. You may need to restart your terminal."
    }
}

# Run installation
Install-Main