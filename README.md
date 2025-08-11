# Tunnel CLI

Modern Terminal User Interface (TUI) for managing tunnels with a beautiful, interactive interface.

## Quick Installation

### One-Line Install (Recommended)

**macOS/Linux:**
```bash
curl -sSL https://tunnel.ovream.com/install.sh | bash
```

**Windows PowerShell:**
```powershell
iwr -useb https://tunnel.ovream.com/install.ps1 | iex
```

### Alternative Installation Methods

**Using pipx (Recommended for isolation):**
```bash
pipx install tunnel-cli
```

**Using pip:**
```bash
pip install tunnel-cli
```

**From source:**
```bash
git clone https://github.com/tunnel/tunnel-cli.git
cd tunnel-cli
pip install .
```

## Usage

After installation, simply run:
```bash
tunnel
```

This launches the interactive TUI with:
- 🔐 **Login Screen** - Secure authentication
- 📊 **Dashboard** - View and manage all your tunnels
- ➕ **Create Tunnels** - Easy tunnel creation with custom or random subdomains
- 🔌 **Connect** - One-click connection to your tunnels
- 📡 **Live Monitoring** - Real-time request tracking

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `N` | New tunnel |
| `C` | Connect to selected tunnel |
| `D` | Delete selected tunnel |
| `R` | Refresh tunnel list |
| `L` | Logout |
| `Q` | Quit application |
| `↑↓` | Navigate |
| `Tab` | Next field |
| `Enter` | Confirm |
| `Esc` | Go back |

### Command Line Options

```bash
tunnel              # Start the TUI
tunnel --version    # Show version
tunnel --help       # Show help
```

### Environment Variables

```bash
TUNNEL_API_URL=http://localhost:8001/api/v1 tunnel  # Use custom API URL
```

## Features

✨ **Beautiful TUI** - Full-screen terminal interface with smooth navigation  
🚀 **Fast & Responsive** - Async operations for instant feedback  
🔒 **Secure** - API key authentication with secure storage  
🌐 **Cross-Platform** - Works on macOS, Linux, and Windows  
📦 **Easy Install** - One command installation  
🎨 **Modern Design** - Clean, intuitive interface  

## System Requirements

- Python 3.7 or higher
- Terminal with Unicode support
- Internet connection

## Configuration

Configuration is stored in `~/.tunnel-cli/config.json` and includes:
- API key (encrypted)
- API URL
- User preferences

## Troubleshooting

**Installation issues:**
- Ensure Python 3.7+ is installed: `python3 --version`
- Try using pipx for isolated installation
- On Windows, run PowerShell as Administrator

**Connection issues:**
- Check your internet connection
- Verify the API URL is correct
- Ensure your account is active

**Display issues:**
- Use a modern terminal (iTerm2, Windows Terminal, etc.)
- Ensure your terminal supports Unicode characters

## Support

- **Documentation**: https://docs.tunnel.ovream.com
- **Issues**: https://github.com/tunnel/tunnel-cli/issues
- **Email**: support@tunnel.ovream.com

## License

MIT License - see LICENSE file for details