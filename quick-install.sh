#!/bin/bash
#
# Tunnel CLI Quick Installer
# One-command installation: curl -sSL https://tunnel.ovream.com/install | bash
#

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo ""
echo "🚀 Installing Tunnel CLI..."
echo ""

# Detect OS
OS="$(uname -s)"
if [[ "$OS" != "Linux" && "$OS" != "Darwin" ]]; then
    echo -e "${RED}❌ Unsupported OS. Use Windows installer for Windows.${NC}"
    exit 1
fi

# Find Python 3
if command -v python3 &>/dev/null; then
    PYTHON="python3"
elif command -v python &>/dev/null && python --version 2>&1 | grep -q "Python 3"; then
    PYTHON="python"
else
    echo -e "${RED}❌ Python 3 not found. Please install Python 3.7+${NC}"
    exit 1
fi

# Install pipx if not present
if ! command -v pipx &>/dev/null; then
    echo "📦 Installing pipx for clean environment..."
    $PYTHON -m pip install --user -q pipx
    $PYTHON -m pipx ensurepath --force
fi

# Get user bin directory
USER_BIN="$HOME/.local/bin"
mkdir -p "$USER_BIN"

# Download and install tunnel-cli
echo "📥 Downloading tunnel CLI..."
TEMP_DIR=$(mktemp -d)
cd "$TEMP_DIR"

# Download the latest release
curl -sL https://github.com/tunnel/tunnel-cli/archive/main.tar.gz | tar xz
cd tunnel-cli-main

# Install using pip with user flag
echo "⚙️  Installing..."
$PYTHON -m pip install --user -q .

# Create a wrapper script that always works
cat > "$USER_BIN/tunnel" << 'EOF'
#!/bin/bash
exec python3 -m tunnel_cli.__main__ "$@"
EOF
chmod +x "$USER_BIN/tunnel"

# Add to PATH for current session
export PATH="$USER_BIN:$PATH"

# Add to shell config if not already there
SHELL_RC=""
if [[ -f "$HOME/.zshrc" ]]; then
    SHELL_RC="$HOME/.zshrc"
elif [[ -f "$HOME/.bashrc" ]]; then
    SHELL_RC="$HOME/.bashrc"
fi

if [[ -n "$SHELL_RC" ]]; then
    if ! grep -q "$USER_BIN" "$SHELL_RC"; then
        echo "" >> "$SHELL_RC"
        echo "# Tunnel CLI" >> "$SHELL_RC"
        echo "export PATH=\"$USER_BIN:\$PATH\"" >> "$SHELL_RC"
    fi
fi

# Clean up
cd /
rm -rf "$TEMP_DIR"

# Success!
echo ""
echo -e "${GREEN}✅ Tunnel CLI installed successfully!${NC}"
echo ""
echo "Run this command to get started:"
echo -e "${YELLOW}  tunnel${NC}"
echo ""
echo "If 'tunnel' command is not found, run:"
echo -e "  ${YELLOW}source ${SHELL_RC}${NC}"
echo "  Or open a new terminal"
echo ""