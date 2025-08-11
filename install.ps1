# Tunnel CLI Installation Script for Windows
# Usage: Run in PowerShell as Administrator:
#   Invoke-WebRequest -Uri https://tunnel.ovream.com/install.ps1 -OutFile install.ps1; .\install.ps1

$ErrorActionPreference = "Stop"

Write-Host "==================================" -ForegroundColor Cyan
Write-Host "  Tunnel CLI Installer (Windows)  " -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")

if (-not $isAdmin) {
    Write-Host "Warning: Not running as administrator. Some features may not work." -ForegroundColor Yellow
    Write-Host "For best results, run PowerShell as Administrator." -ForegroundColor Yellow
    Write-Host ""
}

# Check Python installation
Write-Host "Checking Python installation..." -ForegroundColor Yellow

try {
    $pythonVersion = python --version 2>&1
    if ($pythonVersion -match "Python (\d+)\.(\d+)") {
        $majorVersion = [int]$matches[1]
        $minorVersion = [int]$matches[2]
        
        if ($majorVersion -eq 3 -and $minorVersion -ge 8) {
            Write-Host "✓ Python $majorVersion.$minorVersion found" -ForegroundColor Green
        } else {
            throw "Python 3.8+ required (found $majorVersion.$minorVersion)"
        }
    } else {
        throw "Could not determine Python version"
    }
} catch {
    Write-Host "✗ Python 3.8+ not found" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please install Python 3.8 or later from:" -ForegroundColor Yellow
    Write-Host "https://www.python.org/downloads/" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Make sure to check 'Add Python to PATH' during installation!" -ForegroundColor Yellow
    exit 1
}

# Check pip
Write-Host "Checking pip..." -ForegroundColor Yellow
try {
    $pipVersion = python -m pip --version
    Write-Host "✓ pip found" -ForegroundColor Green
} catch {
    Write-Host "Installing pip..." -ForegroundColor Yellow
    python -m ensurepip --upgrade
}

# Create temp directory for installation
$tempDir = Join-Path $env:TEMP "tunnel-cli-install"
if (Test-Path $tempDir) {
    Remove-Item -Recurse -Force $tempDir
}
New-Item -ItemType Directory -Path $tempDir | Out-Null

Write-Host ""
Write-Host "Downloading Tunnel CLI..." -ForegroundColor Yellow

# Download the CLI package
$downloadUrl = "https://github.com/yourusername/tunnel-cli/archive/refs/heads/main.zip"
$zipFile = Join-Path $tempDir "tunnel-cli.zip"

try {
    # For now, we'll install directly from the local package
    # In production, this would download from GitHub releases or PyPI
    
    Write-Host "Installing Tunnel CLI..." -ForegroundColor Yellow
    
    # Install using pip with user flag
    $pipCommand = "python -m pip install --user --upgrade tunnel-cli"
    
    # If we have a GitHub release URL:
    # $pipCommand = "python -m pip install --user --upgrade https://github.com/yourusername/tunnel-cli/releases/latest/download/tunnel_cli-1.0.0-py3-none-any.whl"
    
    # For now, install from the current directory (for testing)
    if (Test-Path "setup.py") {
        $pipCommand = "python -m pip install --user --upgrade ."
    } else {
        # Install from PyPI when published
        $pipCommand = "python -m pip install --user --upgrade tunnel-cli"
    }
    
    Invoke-Expression $pipCommand
    
    Write-Host "✓ Tunnel CLI installed successfully" -ForegroundColor Green
    
} catch {
    Write-Host "✗ Installation failed: $_" -ForegroundColor Red
    exit 1
} finally {
    # Cleanup
    if (Test-Path $tempDir) {
        Remove-Item -Recurse -Force $tempDir
    }
}

# Add to PATH if needed
$userScriptsPath = python -c "import site; print(site.USER_BASE)"
$userScriptsPath = Join-Path $userScriptsPath "Scripts"

$currentPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($currentPath -notlike "*$userScriptsPath*") {
    Write-Host ""
    Write-Host "Adding Python Scripts to PATH..." -ForegroundColor Yellow
    [Environment]::SetEnvironmentVariable("Path", "$currentPath;$userScriptsPath", "User")
    $env:Path = "$env:Path;$userScriptsPath"
    Write-Host "✓ PATH updated" -ForegroundColor Green
}

Write-Host ""
Write-Host "==================================" -ForegroundColor Green
Write-Host "   Installation Complete!         " -ForegroundColor Green
Write-Host "==================================" -ForegroundColor Green
Write-Host ""
Write-Host "To start using Tunnel CLI:" -ForegroundColor Cyan
Write-Host "  1. Close and reopen your terminal" -ForegroundColor White
Write-Host "  2. Run: tunnel" -ForegroundColor White
Write-Host ""
Write-Host "For help: tunnel --help" -ForegroundColor Gray
Write-Host ""