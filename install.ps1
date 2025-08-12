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
    
    # Create batch file in user profile
    $batchFile = Join-Path $env:USERPROFILE "tunnel.bat"
    $batchContent = "@echo off`n$PythonCmd -m tunnel_cli %*"
    Set-Content -Path $batchFile -Value $batchContent -Force
    
    Write-Success "Created launcher: $batchFile"
    
    # Create PowerShell alias
    $psProfileDir = Split-Path $PROFILE -Parent
    if (!(Test-Path $psProfileDir)) {
        New-Item -ItemType Directory -Path $psProfileDir -Force | Out-Null
    }
    
    $aliasCommand = "function tunnel { & $PythonCmd -m tunnel_cli `$args }"
    
    if (Test-Path $PROFILE) {
        $profileContent = Get-Content $PROFILE -Raw
        if ($profileContent -notmatch "function tunnel") {
            Add-Content -Path $PROFILE -Value "`n# Tunnel CLI alias`n$aliasCommand"
            Write-Success "Added tunnel alias to PowerShell profile"
        }
    } else {
        Set-Content -Path $PROFILE -Value "# Tunnel CLI alias`n$aliasCommand"
        Write-Success "Created PowerShell profile with tunnel alias"
    }
}

# Update PATH
function Update-Path {
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    $userProfile = $env:USERPROFILE
    
    if ($userPath -notlike "*$userProfile*") {
        $newPath = "$userPath;$userProfile"
        [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
        $env:Path = "$env:Path;$userProfile"
        Write-Success "Added $userProfile to PATH"
    } else {
        Write-Info "PATH already includes user profile directory"
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
    Write-Host "To start using Tunnel CLI:" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  Option 1: " -ForegroundColor Yellow -NoNewline
    Write-Host "Run directly"
    Write-Host "    $pythonCmd -m tunnel_cli" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Option 2: " -ForegroundColor Yellow -NoNewline
    Write-Host "Use the batch file"
    Write-Host "    $env:USERPROFILE\tunnel" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Option 3: " -ForegroundColor Yellow -NoNewline
    Write-Host "After restarting PowerShell"
    Write-Host "    tunnel" -ForegroundColor Green
    Write-Host ""
    Write-Host "For help: " -ForegroundColor Gray -NoNewline
    Write-Host "tunnel --help"
    Write-Host "Portal: " -ForegroundColor Gray -NoNewline
    Write-Host "https://tunnel.ovream.com"
    Write-Host ""
    
    if (-not $testResult) {
        Write-Warning "Installation completed with warnings. You may need to restart your terminal."
    }
}

# Run installation
Install-Main