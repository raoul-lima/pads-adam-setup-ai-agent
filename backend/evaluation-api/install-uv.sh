#!/bin/bash

# Adam Backend - uv Installation Script
# This script installs uv package manager for Python

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[UV]${NC} $1"
}

# Check if uv is already installed
if command -v uv &> /dev/null; then
    print_status "uv is already installed: $(uv --version)"
    print_info "Checking if update is needed..."
    
    # Check if we can update uv
    if curl -s https://api.github.com/repos/astral-sh/uv/releases/latest > /dev/null; then
        print_status "uv is up to date and ready to use!"
        exit 0
    else
        print_warning "Could not check for updates, but uv is installed"
        exit 0
    fi
fi

print_info "Installing uv package manager..."

# Detect operating system
OS=""
ARCH=""

case "$(uname -s)" in
    Linux*)     OS="linux";;
    Darwin*)    OS="macos";;
    CYGWIN*)    OS="windows";;
    MINGW*)     OS="windows";;
    *)          print_error "Unsupported operating system: $(uname -s)"; exit 1;;
esac

case "$(uname -m)" in
    x86_64)     ARCH="x86_64";;
    aarch64)    ARCH="aarch64";;
    arm64)      ARCH="aarch64";;
    *)          print_error "Unsupported architecture: $(uname -m)"; exit 1;;
esac

print_info "Detected OS: $OS, Architecture: $ARCH"

# Install uv using the official installer
print_info "Downloading and installing uv..."

if curl -LsSf https://astral.sh/uv/install.sh | sh; then
    print_status "uv installed successfully!"
    
    # Add to PATH for current session - check both common locations
    export PATH="$HOME/.cargo/bin:$HOME/.local/bin:$PATH"
    
    # Source the environment file if it exists
    if [ -f "$HOME/.local/bin/env" ]; then
        source "$HOME/.local/bin/env"
    fi
    
    # Verify installation
    if command -v uv &> /dev/null; then
        print_status "uv is ready to use: $(uv --version)"
        print_info "Installation completed successfully!"
        
        # Show next steps
        echo ""
        print_info "Next steps:"
        echo "  1. Run: source ~/.bashrc (or restart your terminal)"
        echo "  2. Run: uv sync (to install project dependencies)"
        echo "  3. Run: uv run python main.py (to start the application)"
        echo ""
        
    else
        print_error "uv installation completed but uv command not found in PATH"
        print_warning "Please add the following to your PATH:"
        echo "  - $HOME/.cargo/bin (if uv was installed there)"
        echo "  - $HOME/.local/bin (if uv was installed there)"
        print_info "You can also run: source $HOME/.local/bin/env"
        exit 1
    fi
    
else
    print_error "Failed to install uv"
    print_info "Please check your internet connection and try again"
    print_info "You can also install manually from: https://github.com/astral-sh/uv"
    exit 1
fi
