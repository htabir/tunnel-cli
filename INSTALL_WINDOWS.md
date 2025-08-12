# Tunnel CLI Installation Guide for Windows

## 📋 Prerequisites

Before installing Tunnel CLI, ensure you have:

1. **Python 3.8 or later** installed
2. **pip** (Python package manager) installed
3. **PowerShell** or **Command Prompt** access

### Installing Python (if not already installed)

1. Download Python from: https://www.python.org/downloads/
2. Run the installer
3. **IMPORTANT**: Check these options during installation:
   - ✅ "Add Python to PATH"
   - ✅ "Install pip"
   - ✅ "Install for all users" (optional, recommended)

### Verify Python Installation

Open Command Prompt or PowerShell and run:
```cmd
python --version
```

You should see something like: `Python 3.11.0`

## 🚀 Installation Methods

### Method 1: PowerShell Script (Recommended)

Open PowerShell and run:

```powershell
# One-line installation
irm https://tunnel.ovream.com/install-windows.ps1 | iex

# OR download and run
Invoke-WebRequest -Uri https://tunnel.ovream.com/install-windows.ps1 -OutFile install.ps1
.\install.ps1
```

### Method 2: Batch File Installation

1. Download `install-windows.bat` from the repository
2. Right-click and select "Run as Administrator"
3. Follow the prompts

### Method 3: Manual Installation via pip

Open Command Prompt or PowerShell and run:

```cmd
# Install from GitHub
pip install --user git+https://github.com/htabir/tunnel-cli.git

# OR if you've downloaded the source code
cd path\to\tunnel-cli
pip install --user .
```

### Method 4: Direct Python Module Installation

```cmd
# Install required dependencies
pip install --user textual aiohttp requests python-dotenv

# Clone or download the repository
git clone https://github.com/htabir/tunnel-cli.git
cd tunnel-cli

# Install the package
python setup.py install --user
```

## 🔧 Post-Installation Setup

### Adding to PATH (if needed)

If the `tunnel` command is not recognized after installation:

1. Find your Python Scripts directory:
   ```cmd
   python -c "import site; print(site.USER_BASE)"
   ```
   
2. Add the Scripts folder to your PATH:
   - Open System Properties → Advanced → Environment Variables
   - Under "User variables", select "Path" and click "Edit"
   - Add the Scripts path (e.g., `C:\Users\YourName\AppData\Roaming\Python\Python311\Scripts`)
   - Click OK and restart your terminal

### Creating a Shortcut

Create a batch file for easy access:

1. Create a new file called `tunnel.bat` in your user folder
2. Add this content:
   ```batch
   @echo off
   python -m tunnel_cli %*
   ```
3. Save the file
4. Now you can run `tunnel` from anywhere

## 🎮 Running Tunnel CLI

After installation, you can run Tunnel CLI using any of these methods:

### Method 1: Direct Command (after PATH setup)
```cmd
tunnel
```

### Method 2: Python Module
```cmd
python -m tunnel_cli
```

### Method 3: Using the Batch File
```cmd
%USERPROFILE%\tunnel
```

## 🧪 Verify Installation

Test if Tunnel CLI is properly installed:

```cmd
# Check version
tunnel --version

# Show help
tunnel --help

# Start the TUI
tunnel
```

## 🔍 Troubleshooting

### "tunnel" is not recognized

**Solution**: The Scripts directory is not in PATH. Either:
- Add it to PATH (see Post-Installation Setup)
- Use `python -m tunnel_cli` instead

### "Python is not recognized"

**Solution**: Python is not installed or not in PATH:
1. Reinstall Python with "Add to PATH" checked
2. Or manually add Python to PATH

### ImportError: No module named 'textual'

**Solution**: Dependencies not installed:
```cmd
pip install --user textual aiohttp requests python-dotenv
```

### Permission Denied Error

**Solution**: Use `--user` flag with pip:
```cmd
pip install --user tunnel-cli
```

### SSL Certificate Error

**Solution**: Update certificates:
```cmd
pip install --upgrade certifi
```

## 🆘 Getting Help

- **Documentation**: https://tunnel.ovream.com/docs
- **GitHub Issues**: https://github.com/htabir/tunnel-cli/issues
- **Portal**: https://tunnel.ovream.com

## 📦 Uninstallation

To remove Tunnel CLI:

```cmd
pip uninstall tunnel-cli
```

Or remove manually:
1. Delete the tunnel-cli package from site-packages
2. Remove any batch files or shortcuts created
3. Clean up PATH if modified

## 🔄 Updating

To update to the latest version:

```cmd
pip install --user --upgrade tunnel-cli

# OR from GitHub
pip install --user --upgrade git+https://github.com/htabir/tunnel-cli.git
```

## 💡 Tips for Windows Users

1. **Use PowerShell** instead of Command Prompt for better compatibility
2. **Run as Administrator** if you encounter permission issues
3. **Restart your terminal** after installation for PATH changes to take effect
4. **Create a desktop shortcut** for easy access:
   - Right-click on desktop → New → Shortcut
   - Location: `python -m tunnel_cli`
   - Name: "Tunnel CLI"

## 🎯 Quick Start After Installation

1. Run `tunnel` or `python -m tunnel_cli`
2. Choose authentication method:
   - **Browser Auth** (recommended): Press 'B'
   - **Manual API Key**: Press 'M'
3. Create your first tunnel:
   - Press 'N' for new tunnel
   - Enter local port (e.g., 3000)
   - Choose subdomain or leave empty for random
4. Your tunnel is ready! Access it at: `https://[subdomain].tunnel.ovream.com`

---

*For other platforms, see the main [README.md](README.md)*