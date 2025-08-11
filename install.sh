#!/bin/bash
#
# Tunnel CLI Installer Script
# Supports macOS and Linux
#

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

# Verify installation
print_info "Verifying installation..."

if command -v tunnel &> /dev/null; then
    print_success "Installation verified"
    echo ""
    echo "======================================"
    echo "    Installation Complete!            "
    echo "======================================"
    echo ""
    echo "You can now use the tunnel command:"
    echo "  tunnel              - Start the TUI"
    echo "  tunnel --help       - Show help"
    echo "  tunnel --version    - Show version"
    echo ""
    
    # Check if PATH needs updating
    if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
        echo "Note: You may need to add ~/.local/bin to your PATH"
        echo "Add this line to your ~/.bashrc or ~/.zshrc:"
        echo '  export PATH="$PATH:$HOME/.local/bin"'
        echo ""
        echo "Or restart your terminal for changes to take effect."
    fi
else
    print_error "Installation failed - 'tunnel' command not found"
    echo "Please check the installation logs above for errors"
    exit 1
fi

echo ""
print_success "Happy tunneling! 🚀"