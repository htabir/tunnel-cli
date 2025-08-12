#!/bin/bash
# Tunnel CLI Universal Installer for Linux/macOS
# Usage: curl -sSL https://tunnel.ovream.com/install | bash
# or: wget -qO- https://tunnel.ovream.com/install | bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Print colored output
print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${YELLOW}→${NC} $1"
}

# Header
echo "======================================"
echo "    Tunnel CLI Installer v1.0.0      "
echo "======================================"
echo ""

# Check OS
OS="$(uname -s)"
case "${OS}" in
    Linux*)     OS_TYPE=Linux;;
    Darwin*)    OS_TYPE=Mac;;
    *)          
        print_error "Unsupported OS: ${OS}"
        echo "This installer supports macOS and Linux only."
        echo "For Windows, please use install.ps1"
        exit 1
        ;;
esac

print_info "Detected OS: ${OS_TYPE}"

# Check Python
print_info "Checking Python installation..."

# Try to find Python 3
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    # Check if it's Python 3
    if python --version 2>&1 | grep -q "Python 3"; then
        PYTHON_CMD="python"
    else
        print_error "Python 3 is required but not found"
        echo "Please install Python 3.7 or higher"
        exit 1
    fi
else
    print_error "Python is not installed"
    echo "Please install Python 3.7 or higher"
    
    if [ "$OS_TYPE" = "Mac" ]; then
        echo "On macOS, you can install Python using:"
        echo "  brew install python3"
    else
        echo "On Linux, you can install Python using:"
        echo "  sudo apt-get install python3 python3-pip  # Debian/Ubuntu"
        echo "  sudo yum install python3 python3-pip      # RedHat/CentOS"
    fi
    exit 1
fi

# Check Python version
PYTHON_VERSION=$($PYTHON_CMD -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
REQUIRED_VERSION="3.7"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    print_error "Python $REQUIRED_VERSION or higher is required (found $PYTHON_VERSION)"
    exit 1
fi

print_success "Python $PYTHON_VERSION found"

# Check pip
print_info "Checking pip installation..."

if ! $PYTHON_CMD -m pip --version &> /dev/null; then
    print_error "pip is not installed"
    echo "Installing pip..."
    
    if [ "$OS_TYPE" = "Mac" ]; then
        $PYTHON_CMD -m ensurepip
    else
        curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
        $PYTHON_CMD get-pip.py
        rm get-pip.py
    fi
fi

print_success "pip is installed"

# Check pipx (recommended installer)
print_info "Checking pipx installation..."

if ! command -v pipx &> /dev/null; then
    print_info "pipx not found. Installing pipx for isolated environment..."
    $PYTHON_CMD -m pip install --user pipx
    $PYTHON_CMD -m pipx ensurepath
    
    # Add to current session
    export PATH="$PATH:$HOME/.local/bin"
    
    print_success "pipx installed"
else
    print_success "pipx is already installed"
fi

# Install tunnel-cli
print_info "Installing tunnel-cli..."

# Create temporary directory for installation
TEMP_DIR=$(mktemp -d)
cd "$TEMP_DIR"

# Download the package
print_info "Downloading tunnel-cli package..."
curl -L -o tunnel-cli.tar.gz https://github.com/tunnel/tunnel-cli/releases/latest/download/tunnel-cli.tar.gz 2>/dev/null || {
    # Fallback to git clone if release not available
    print_info "Release not found, installing from source..."
    git clone https://github.com/tunnel/tunnel-cli.git .
}

# Install using pipx for isolation
if command -v pipx &> /dev/null; then
    pipx install .
else
    # Fallback to pip
    $PYTHON_CMD -m pip install --user .
fi

# Clean up
cd - > /dev/null
rm -rf "$TEMP_DIR"

print_success "tunnel-cli installed successfully!"

# Create tunnel alias/command
print_info "Setting up 'tunnel' command..."

# Determine the user's shell
SHELL_NAME=$(basename "$SHELL")
SHELL_RC=""

case "$SHELL_NAME" in
    bash)
        SHELL_RC="$HOME/.bashrc"
        ;;
    zsh)
        SHELL_RC="$HOME/.zshrc"
        ;;
    fish)
        SHELL_RC="$HOME/.config/fish/config.fish"
        ;;
    *)
        SHELL_RC="$HOME/.profile"
        ;;
esac

# Create a universal tunnel script in ~/.local/bin
mkdir -p "$HOME/.local/bin"
TUNNEL_SCRIPT="$HOME/.local/bin/tunnel"

cat > "$TUNNEL_SCRIPT" << EOF
#!/usr/bin/env bash
# Tunnel CLI launcher script
exec $PYTHON_CMD -m tunnel_cli "\$@"
EOF

chmod +x "$TUNNEL_SCRIPT"
print_success "Created launcher script at $TUNNEL_SCRIPT"

# Add PATH and alias to shell config if needed
if [ -f "$SHELL_RC" ]; then
    # Check if .local/bin is in PATH
    if ! grep -q "export PATH.*HOME/.local/bin" "$SHELL_RC"; then
        echo "" >> "$SHELL_RC"
        echo "# Added by Tunnel CLI installer" >> "$SHELL_RC"
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$SHELL_RC"
        print_success "Added ~/.local/bin to PATH in $SHELL_RC"
    fi
    
    # Add alias as backup
    if ! grep -q "alias tunnel=" "$SHELL_RC"; then
        echo "alias tunnel='$PYTHON_CMD -m tunnel_cli'" >> "$SHELL_RC"
        print_success "Added tunnel alias to $SHELL_RC"
    fi
else
    # Create shell config with PATH and alias
    echo "# Added by Tunnel CLI installer" > "$SHELL_RC"
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$SHELL_RC"
    echo "alias tunnel='$PYTHON_CMD -m tunnel_cli'" >> "$SHELL_RC"
    print_success "Created $SHELL_RC with tunnel command"
fi

# For macOS, also update .bash_profile if it exists (for Terminal.app compatibility)
if [ "$OS_TYPE" = "Mac" ] && [ -f "$HOME/.bash_profile" ]; then
    if ! grep -q "export PATH.*HOME/.local/bin" "$HOME/.bash_profile"; then
        echo "" >> "$HOME/.bash_profile"
        echo "# Added by Tunnel CLI installer" >> "$HOME/.bash_profile"
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bash_profile"
        echo "alias tunnel='$PYTHON_CMD -m tunnel_cli'" >> "$HOME/.bash_profile"
        print_success "Updated .bash_profile for macOS Terminal.app"
    fi
fi

# Verify installation
print_info "Verifying installation..."

# Test if the module works
if $PYTHON_CMD -m tunnel_cli --version &> /dev/null; then
    print_success "Installation verified - tunnel_cli module is working"
    
    echo ""
    echo "======================================"
    echo "    Installation Complete! 🎉        "
    echo "======================================"
    echo ""
    echo "The 'tunnel' command has been installed!"
    echo ""
    echo "To start using it:"
    echo ""
    
    # Check if we need to reload shell
    if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
        echo "  Option 1: Reload your shell configuration"
        echo "    source $SHELL_RC"
        echo ""
        echo "  Option 2: Restart your terminal"
        echo ""
        echo "  Option 3: Use the full command now"
        echo "    $PYTHON_CMD -m tunnel_cli"
    else
        # PATH is already set, check if script exists
        if [ -x "$TUNNEL_SCRIPT" ]; then
            echo "  tunnel              - Start the TUI"
            echo "  tunnel --help       - Show help"
            echo "  tunnel --version    - Show version"
        else
            echo "  Reload your shell or run:"
            echo "    source $SHELL_RC"
            echo ""
            echo "  Then use:"
            echo "    tunnel              - Start the TUI"
        fi
    fi
    
    echo ""
    echo "After reloading your shell, you can run 'tunnel' from anywhere!"
else
    print_error "Installation failed - tunnel_cli module not working"
    echo "Please check the installation logs above for errors"
    exit 1
fi

echo ""
print_success "Happy tunneling! 🚀"