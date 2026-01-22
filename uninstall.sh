#!/bin/bash

# Plasma Spotlight Uninstaller
# Safe for curl | bash usage

uninstall_plasma_spotlight() {
    set -e # Exit on any error

    # Configuration
    INSTALL_DIR="$HOME/.local/share/plasma-spotlight"
    BIN_DIR="$HOME/.local/bin"
    CONFIG_DIR="$HOME/.config/plasma-spotlight"
    CONFIG_FILE="$CONFIG_DIR/config.json"
    SCRIPT_NAME="plasma-spotlight"
    WRAPPER_PATH="$BIN_DIR/$SCRIPT_NAME"

    echo "Uninstalling Plasma Spotlight..."

    # Step 1: Uninstall SDDM theme and systemd timer (if installed)
    if [ -x "$WRAPPER_PATH" ]; then
        echo "Removing SDDM theme and systemd timer..."
        "$WRAPPER_PATH" --_internal-uninstall || echo "Note: SDDM theme or timer may not have been installed"
    fi

    # Step 2: Remove installation directory
    if [ -d "$INSTALL_DIR" ]; then
        echo "Removing installation directory: $INSTALL_DIR"
        rm -rf "$INSTALL_DIR"
    fi

    # Step 3: Remove executable symlink
    if [ -f "$WRAPPER_PATH" ] || [ -L "$WRAPPER_PATH" ]; then
        echo "Removing executable: $WRAPPER_PATH"
        rm -f "$WRAPPER_PATH"
    fi

    # Step 4: Optionally remove configuration directory
    # Try to read wallpaper paths from config before we delete it
    BING_PATH=""
    SPOTLIGHT_PATH=""
    if [ -f "$CONFIG_FILE" ]; then
        # Parse JSON using grep/sed (no dependencies)
        BING_PATH=$(grep -o '"save_path_bing"[[:space:]]*:[[:space:]]*"[^"]*"' "$CONFIG_FILE" 2>/dev/null | sed 's/.*"\([^"]*\)".*/\1/' | sed "s|~|$HOME|")
        SPOTLIGHT_PATH=$(grep -o '"save_path_spotlight"[[:space:]]*:[[:space:]]*"[^"]*"' "$CONFIG_FILE" 2>/dev/null | sed 's/.*"\([^"]*\)".*/\1/' | sed "s|~|$HOME|")
    fi

    echo ""
    # Check if running in interactive mode
    if [ -t 0 ]; then
        read -p "Remove configuration directory (~/.config/plasma-spotlight)? [y/N] " -n 1 -r </dev/tty
        echo
    else
        # Non-interactive mode, default to No
        echo "Non-interactive mode detected. Keeping configuration directory."
        REPLY="N"
    fi

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if [ -d "$CONFIG_DIR" ]; then
            echo "Removing config: $CONFIG_DIR"
            rm -rf "$CONFIG_DIR"
        fi
    fi

    # Show wallpaper locations (if we found them)
    echo ""
    if [ -n "$BING_PATH" ] || [ -n "$SPOTLIGHT_PATH" ]; then
        echo "Note: Downloaded wallpapers were not removed:"
        [ -n "$BING_PATH" ] && echo "  - Bing: $BING_PATH"
        [ -n "$SPOTLIGHT_PATH" ] && echo "  - Spotlight: $SPOTLIGHT_PATH"
    else
        echo "Note: Downloaded wallpapers in ~/Pictures/Wallpapers/ were not removed."
    fi
    echo "You can manually delete them if desired."

    echo "--------------------------------------------------"
    echo "✓ Plasma Spotlight has been uninstalled."
    echo "--------------------------------------------------"
}

# Execute the uninstaller (only runs if the full script downloaded)
uninstall_plasma_spotlight "$@"
