# Tunnel CLI Installation Script for Windows
# Usage: Run in PowerShell:
#   irm https://tunnel.ovream.com/install-windows.ps1 | iex
#   OR
#   Invoke-WebRequest -Uri https://tunnel.ovream.com/install-windows.ps1 -OutFile install.ps1; .\install.ps1

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "╔══════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║   Tunnel CLI Installer for Windows   ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Function to test Python command
function Test-PythonCommand {
    param([string]$cmd)
    try {
        $result = & $cmd --version 2>&1
        if ($result -match "Python (\d+)\.(\d+)") {
            return @{
                Success = $true
                Major = [int]$matches[1]
                Minor = [int]$matches[2]
                Command = $cmd
                Version = $result
            }
        }
    } catch {}
    return @{Success = $false}
}

# Check Python installation - try multiple commands
Write-Host "🔍 Checking Python installation..." -ForegroundColor Yellow

$pythonCmd = $null
$pythonInfo = $null

# Try different Python commands
$pythonCommands = @("python", "python3", "py")
foreach ($cmd in $pythonCommands) {
    $result = Test-PythonCommand $cmd
    if ($result.Success -and $result.Major -eq 3 -and $result.Minor -ge 8) {
        $pythonCmd = $cmd
        $pythonInfo = $result
        break
    }
}

if ($null -eq $pythonCmd) {
    Write-Host "❌ Python 3.8+ not found" -ForegroundColor Red
    Write-Host ""
    Write-Host "📦 Please install Python from:" -ForegroundColor Yellow
    Write-Host "   https://www.python.org/downloads/" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "⚠️  IMPORTANT: During installation, make sure to:" -ForegroundColor Yellow
    Write-Host "   1. Check 'Add Python to PATH'" -ForegroundColor White
    Write-Host "   2. Check 'Install pip'" -ForegroundColor White
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "✅ Found $($pythonInfo.Version)" -ForegroundColor Green

# Check pip
Write-Host "🔍 Checking pip..." -ForegroundColor Yellow
try {
    $pipVersion = & $pythonCmd -m pip --version 2>&1
    if ($pipVersion -match "pip") {
        Write-Host "✅ pip is installed" -ForegroundColor Green
    } else {
        throw "pip not found"
    }
} catch {
    Write-Host "📦 Installing pip..." -ForegroundColor Yellow
    & $pythonCmd -m ensurepip --upgrade
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Failed to install pip" -ForegroundColor Red
        exit 1
    }
}

# Upgrade pip
Write-Host "📦 Upgrading pip..." -ForegroundColor Yellow
& $pythonCmd -m pip install --upgrade pip --quiet
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ pip upgraded" -ForegroundColor Green
}

# Install required dependencies
Write-Host ""
Write-Host "📦 Installing dependencies..." -ForegroundColor Yellow

$dependencies = @(
    "textual>=0.47.0",
    "aiohttp>=3.9.0",
    "requests>=2.31.0",
    "python-dotenv>=1.0.0"
)

foreach ($dep in $dependencies) {
    Write-Host "   Installing $dep..." -ForegroundColor Gray
    & $pythonCmd -m pip install --user "$dep" --quiet
    if ($LASTEXITCODE -ne 0) {
        Write-Host "⚠️  Warning: Failed to install $dep" -ForegroundColor Yellow
    }
}

Write-Host "✅ Dependencies installed" -ForegroundColor Green

# Create the tunnel CLI package
Write-Host ""
Write-Host "📦 Installing Tunnel CLI..." -ForegroundColor Yellow

# Create a temporary directory
$tempDir = Join-Path $env:TEMP "tunnel-cli-install"
if (Test-Path $tempDir) {
    Remove-Item -Recurse -Force $tempDir
}
New-Item -ItemType Directory -Path $tempDir | Out-Null

# Download from GitHub (replace with your actual GitHub repo)
$githubRepo = "htabir/tunnel-cli"
$downloadUrl = "https://github.com/$githubRepo/archive/refs/heads/main.zip"
$zipFile = Join-Path $tempDir "tunnel-cli.zip"
$extractDir = Join-Path $tempDir "tunnel-cli-main"

try {
    Write-Host "   Downloading from GitHub..." -ForegroundColor Gray
    Invoke-WebRequest -Uri $downloadUrl -OutFile $zipFile -UseBasicParsing
    
    Write-Host "   Extracting files..." -ForegroundColor Gray
    Expand-Archive -Path $zipFile -DestinationPath $tempDir -Force
    
    Write-Host "   Installing package..." -ForegroundColor Gray
    Set-Location $extractDir
    & $pythonCmd -m pip install --user . --quiet
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Tunnel CLI installed successfully" -ForegroundColor Green
    } else {
        throw "Installation failed with exit code $LASTEXITCODE"
    }
} catch {
    # Fallback: Try to install from PyPI (when published)
    Write-Host "   Trying alternative installation method..." -ForegroundColor Yellow
    & $pythonCmd -m pip install --user tunnel-cli
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Installation failed: $_" -ForegroundColor Red
        Write-Host ""
        Write-Host "📝 Manual installation steps:" -ForegroundColor Yellow
        Write-Host "   1. Download the CLI from: https://github.com/$githubRepo" -ForegroundColor White
        Write-Host "   2. Extract the files" -ForegroundColor White
        Write-Host "   3. Open terminal in the extracted folder" -ForegroundColor White
        Write-Host "   4. Run: $pythonCmd -m pip install ." -ForegroundColor White
        Read-Host "Press Enter to exit"
        exit 1
    }
} finally {
    # Cleanup
    Set-Location $env:TEMP
    if (Test-Path $tempDir) {
        Remove-Item -Recurse -Force $tempDir -ErrorAction SilentlyContinue
    }
}

# Find where the tunnel command was installed
Write-Host ""
Write-Host "🔍 Locating installation..." -ForegroundColor Yellow

$userBase = & $pythonCmd -c "import site; print(site.USER_BASE)" 2>$null
$scriptsPath = Join-Path $userBase "Scripts"
$tunnelExe = Join-Path $scriptsPath "tunnel.exe"
$tunnelPy = Join-Path $scriptsPath "tunnel"

$tunnelFound = $false
if (Test-Path $tunnelExe) {
    $tunnelPath = $tunnelExe
    $tunnelFound = $true
} elseif (Test-Path $tunnelPy) {
    $tunnelPath = $tunnelPy
    $tunnelFound = $true
}

# Add to PATH if needed
$currentUserPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($currentUserPath -notlike "*$scriptsPath*") {
    Write-Host "📝 Adding to PATH..." -ForegroundColor Yellow
    $newPath = "$currentUserPath;$scriptsPath"
    [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
    $env:Path = "$env:Path;$scriptsPath"
    Write-Host "✅ PATH updated" -ForegroundColor Green
    Write-Host "   ⚠️  You may need to restart your terminal" -ForegroundColor Yellow
} else {
    Write-Host "✅ Scripts directory already in PATH" -ForegroundColor Green
}

# Create a batch file for easy execution
$batchFile = Join-Path $env:USERPROFILE "tunnel.bat"
$batchContent = "@echo off`n$pythonCmd -m tunnel_cli %*"
Set-Content -Path $batchFile -Value $batchContent -Force
Write-Host "✅ Created shortcut: $batchFile" -ForegroundColor Green

Write-Host ""
Write-Host "╔══════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║     Installation Complete! 🎉        ║" -ForegroundColor Green
Write-Host "╚══════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "📌 To start using Tunnel CLI:" -ForegroundColor Cyan
Write-Host ""
Write-Host "   Option 1 (Recommended):" -ForegroundColor Yellow
Write-Host "   Close and reopen your terminal, then run:" -ForegroundColor White
Write-Host "   > tunnel" -ForegroundColor Green
Write-Host ""
Write-Host "   Option 2 (Works immediately):" -ForegroundColor Yellow
Write-Host "   > $pythonCmd -m tunnel_cli" -ForegroundColor Green
Write-Host ""
Write-Host "   Option 3 (From anywhere):" -ForegroundColor Yellow
Write-Host "   > $env:USERPROFILE\tunnel" -ForegroundColor Green
Write-Host ""
Write-Host "📚 For help: tunnel --help" -ForegroundColor Gray
Write-Host "🌐 Portal: https://tunnel.ovream.com" -ForegroundColor Gray
Write-Host ""

# Test the installation
Write-Host "🧪 Testing installation..." -ForegroundColor Yellow
try {
    $testOutput = & $pythonCmd -m tunnel_cli --help 2>&1
    if ($testOutput -match "Tunnel CLI") {
        Write-Host "✅ Installation test passed!" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Installation may need troubleshooting" -ForegroundColor Yellow
    }
} catch {
    Write-Host "⚠️  Could not verify installation" -ForegroundColor Yellow
}

Write-Host ""
Read-Host "Press Enter to exit"