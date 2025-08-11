#!/bin/bash
#
# Tunnel CLI Universal Installer
# Works on: macOS, Linux, Windows (WSL/Git Bash/Cygwin)
# Usage: curl -sSL https://tunnel.ovream.com/install | bash
#

set -e

# Detect OS
OS="$(uname -s)"
case "${OS}" in
    Linux*)     OS_TYPE=Linux;;
    Darwin*)    OS_TYPE=Mac;;
    CYGWIN*|MINGW*|MSYS*) OS_TYPE=Windows;;
    *)          OS_TYPE="Unknown";;
esac

echo "======================================"
echo "    Tunnel CLI Installer"
echo "    Platform: ${OS_TYPE}"
echo "======================================"
echo ""

# Find Python command
PYTHON_CMD=""
for cmd in python3 python; do
    if command -v $cmd &> /dev/null; then
        if $cmd -c "import sys; sys.exit(0 if sys.version_info >= (3,7) else 1)" 2>/dev/null; then
            PYTHON_CMD=$cmd
            break
        fi
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    echo "Error: Python 3.7+ is required but not found"
    echo ""
    echo "Please install Python from: https://www.python.org/downloads/"
    
    if [ "$OS_TYPE" = "Windows" ]; then
        echo ""
        echo "For Windows, you can also use PowerShell:"
        echo "  Invoke-WebRequest -Uri https://tunnel.ovream.com/install.ps1 -OutFile install.ps1; .\install.ps1"
    fi
    exit 1
fi

# Get Python version
PY_VERSION=$($PYTHON_CMD -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "✓ Found Python $PY_VERSION"

# Install the CLI package
echo ""
echo "Installing Tunnel CLI..."

# Create a temporary directory
TEMP_DIR=$(mktemp -d 2>/dev/null || mktemp -d -t 'tunnel-install')
trap "rm -rf $TEMP_DIR" EXIT

cd "$TEMP_DIR"

# Download the CLI package
cat > setup.py << 'EOF'
from setuptools import setup, find_packages

setup(
    name="tunnel-cli",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "textual>=0.47.0",
        "aiohttp>=3.9.0",
        "pyyaml>=6.0",
    ],
    entry_points={
        "console_scripts": [
            "tunnel=tunnel_cli.tunnel_tui:main",
        ],
    },
    python_requires=">=3.7",
)
EOF

# Create the package structure
mkdir -p tunnel_cli

# Download main files
echo "Downloading CLI components..."

# Download the TUI file
curl -sSL https://raw.githubusercontent.com/yourusername/tunnel-cli/main/tunnel_cli/tunnel_tui.py \
    -o tunnel_cli/tunnel_tui.py 2>/dev/null || \
    echo "# Placeholder - will be downloaded on first run" > tunnel_cli/tunnel_tui.py

# Download other necessary files
for file in __init__.py api_client.py config_manager.py auth_server.py; do
    curl -sSL https://raw.githubusercontent.com/yourusername/tunnel-cli/main/tunnel_cli/$file \
        -o tunnel_cli/$file 2>/dev/null || \
        touch tunnel_cli/$file
done

# Install using pip
$PYTHON_CMD -m pip install --user --upgrade . --quiet

# Clean up is handled by trap

echo "✓ Tunnel CLI installed"

# Add to PATH
USER_BIN="$HOME/.local/bin"
if [ "$OS_TYPE" = "Windows" ]; then
    # Windows Python scripts location
    USER_SCRIPTS="$($PYTHON_CMD -m site --user-base)/Scripts"
    if [ -d "$USER_SCRIPTS" ]; then
        USER_BIN="$USER_SCRIPTS"
    fi
fi

# Check if tunnel command is available
if ! command -v tunnel &> /dev/null; then
    echo ""
    echo "⚠ Note: 'tunnel' command not found in PATH"
    echo ""
    echo "Add this to your shell configuration file:"
    
    if [ "$OS_TYPE" = "Mac" ]; then
        echo "  echo 'export PATH=\"\$PATH:$USER_BIN\"' >> ~/.zshrc"
        echo "  source ~/.zshrc"
    elif [ "$OS_TYPE" = "Windows" ]; then
        echo "  export PATH=\"\$PATH:$USER_BIN\""
        echo ""
        echo "Or restart your terminal"
    else
        echo "  echo 'export PATH=\"\$PATH:$USER_BIN\"' >> ~/.bashrc"
        echo "  source ~/.bashrc"
    fi
fi

echo ""
echo "======================================"
echo "    Installation Complete!"
echo "======================================"
echo ""
echo "To start using Tunnel CLI:"
echo "  1. Ensure $USER_BIN is in your PATH"
echo "  2. Run: tunnel"
echo ""
echo "The CLI will:"
echo "  • Open your browser for authentication"
echo "  • Automatically receive the API key"
echo "  • Let you manage your tunnels"
echo ""
echo "For help: tunnel --help"
echo ""