#!/bin/bash

# Plasma Spotlight Installer
# Safe for curl | bash usage

install_plasma_spotlight() {
    set -e  # Exit on any error

    # Configuration
    INSTALL_DIR="$HOME/.local/share/plasma-spotlight"
    BIN_DIR="$HOME/.local/bin"
    REPO_URL="https://github.com/yourusername/plasma-spotlight.git"  # IMPORTANT: Update before release!
    SCRIPT_NAME="plasma-spotlight"

    echo "Installing Plasma Spotlight..."

    # Prerequisites check
    if ! command -v git &> /dev/null; then
        echo "Error: git is not installed."
        exit 1
    fi

    if ! command -v python3 &> /dev/null; then
        echo "Error: python3 is not installed."
        exit 1
    fi
    
    # Check for KDE Plasma 6 (kwriteconfig6 is required)
    if ! command -v kwriteconfig6 &> /dev/null; then
        echo "Warning: kwriteconfig6 not found. KDE Plasma 6 may not be installed."
        echo "This tool requires KDE Plasma 6 for lock screen integration."
        read -p "Continue anyway? [y/N] " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Installation cancelled."
            exit 1
        fi
    fi

    # Ensure directories exist
    mkdir -p "$INSTALL_DIR"
    mkdir -p "$BIN_DIR"
    
    # Check if ~/.local/bin is in PATH before installation
    if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
        echo ""
        echo "⚠ Warning: $BIN_DIR is not in your PATH."
        echo "The installation will continue, but you won't be able to run the command until you add it."
        echo ""
        echo "Add this line to your ~/.bashrc or ~/.zshrc:"
        echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
        echo ""
        read -p "Press Enter to continue with installation..."
        echo ""
    fi

    # Install Logic
    if [ -f "pyproject.toml" ] && [ -d ".git" ]; then
        echo "Detected local repository. Syncing files..."
        if command -v rsync &> /dev/null; then
            rsync -av --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' ./ "$INSTALL_DIR/"
        else
            cp -r . "$INSTALL_DIR/"
        fi
    else
        # Remote install (curl | bash)
        if [ -d "$INSTALL_DIR/.git" ]; then
            echo "Updating existing installation..."
            git -C "$INSTALL_DIR" pull -q
        else
            echo "Cloning repository from $REPO_URL..."
            git clone -q "$REPO_URL" "$INSTALL_DIR"
        fi
    fi

    # Create executable wrapper
    WRAPPER_PATH="$BIN_DIR/$SCRIPT_NAME"

    cat <<EOF > "$WRAPPER_PATH"
#!/bin/bash
export PYTHONPATH="$INSTALL_DIR:\$PYTHONPATH"
exec python3 -m plasma_spotlight "\$@"
EOF

    chmod +x "$WRAPPER_PATH"

    echo "--------------------------------------------------"
    echo "✓ Success! Installed to: $INSTALL_DIR"
    echo "✓ Executable created at: $WRAPPER_PATH"
    echo ""
    
    # Check if ~/.local/bin is in PATH (show message only if not already shown)
    if [[ ":$PATH:" == *":$BIN_DIR:"* ]]; then
        echo "You can now run:"
        echo "  $SCRIPT_NAME --help"
        echo "  $SCRIPT_NAME --setup-sddm-theme"
        echo "  $SCRIPT_NAME --update-lockscreen --update-sddm"
    else:
        echo "⚠ Remember to add $BIN_DIR to your PATH:"
        echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
        echo ""
        echo "Then restart your terminal or run: source ~/.bashrc"
    fi
    echo "--------------------------------------------------"
}

# Execute the installer (only runs if the full script downloaded)
install_plasma_spotlight "$@"
