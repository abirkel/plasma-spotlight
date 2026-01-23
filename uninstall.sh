#!/bin/bash

# Plasma Spotlight Uninstaller
# Safe for curl | bash usage

uninstall_plasma_spotlight() {
	# No set -e - uninstall should be best-effort
	# Continue cleaning up even if some operations fail

	# Configuration
	INSTALL_DIR="$HOME/.local/share/plasma-spotlight"
	BIN_DIR="$HOME/.local/bin"
	CONFIG_DIR="$HOME/.config/plasma-spotlight"
	CONFIG_FILE="$CONFIG_DIR/config.json"
	SYSTEMD_USER_DIR="$HOME/.config/systemd/user"
	SCRIPT_NAME="plasma-spotlight"
	WRAPPER_PATH="$BIN_DIR/$SCRIPT_NAME"

	echo "Uninstalling Plasma Spotlight..."
	echo ""

	# ============================================
	# SYSTEM COMPONENT REMOVAL (REQUIRES SUDO)
	# ============================================

	echo "Removing system components (requires sudo)..."

	if sudo bash <<EOSUDO; then
set -e

SDDM_THEME_DIR="/var/sddm_themes/themes/plasma-spotlight"
SDDM_CONF="/etc/sddm.conf.d/plasma-spotlight.conf"
USER_BG_CACHE="/var/cache/plasma-spotlight"

# Remove SDDM theme directory
if [ -d "\$SDDM_THEME_DIR" ]; then
    rm -rf "\$SDDM_THEME_DIR"
    echo "Removed SDDM theme"
fi

# Remove SDDM configuration
if [ -f "\$SDDM_CONF" ]; then
    rm -f "\$SDDM_CONF"
    echo "Removed SDDM config"
fi

# Remove cache directory
if [ -d "\$USER_BG_CACHE" ]; then
    rm -rf "\$USER_BG_CACHE"
    echo "Removed background cache"
fi

echo "System components removed"
EOSUDO
		echo ""
	else
		echo ""
		echo "⚠ Warning: System component removal failed"
		echo "  You may need to manually remove:"
		echo "  - /var/sddm_themes/themes/plasma-spotlight/"
		echo "  - /etc/sddm.conf.d/plasma-spotlight.conf"
		echo "  - /var/cache/plasma-spotlight/"
		echo ""
		echo "Continuing with user component cleanup..."
		echo ""
	fi

	# ============================================
	# USER COMPONENT REMOVAL (NO SUDO)
	# ============================================

	echo "Removing user components..."

	# 1. Disable and remove systemd timer
	if [ -f "$SYSTEMD_USER_DIR/plasma-spotlight.timer" ]; then
		systemctl --user disable --now plasma-spotlight.timer 2>/dev/null || true
		rm -f "$SYSTEMD_USER_DIR/plasma-spotlight.timer"
		echo "Removed systemd timer"
	fi

	if [ -f "$SYSTEMD_USER_DIR/plasma-spotlight.service" ]; then
		rm -f "$SYSTEMD_USER_DIR/plasma-spotlight.service"
		echo "Removed systemd service"
	fi

	systemctl --user daemon-reload 2>/dev/null || true

	# 2. Remove user background symlink
	if [ -L "$HOME/.local/share/plasma-spotlight/current.jpg" ] || [ -f "$HOME/.local/share/plasma-spotlight/current.jpg" ]; then
		rm -f "$HOME/.local/share/plasma-spotlight/current.jpg"
		echo "Removed legacy user background symlink"
	fi

	# Remove legacy directory if empty
	if [ -d "$HOME/.local/share/plasma-spotlight" ]; then
		rmdir "$HOME/.local/share/plasma-spotlight" 2>/dev/null || true
	fi

	echo "User components removed"
	echo ""

	# ============================================
	# REMOVE INSTALLATION FILES
	# ============================================

	# Remove installation directory
	if [ -d "$INSTALL_DIR" ]; then
		echo "Removing installation directory: $INSTALL_DIR"
		rm -rf "$INSTALL_DIR"
	fi

	# Remove executable
	if [ -f "$WRAPPER_PATH" ] || [ -L "$WRAPPER_PATH" ]; then
		echo "Removing executable: $WRAPPER_PATH"
		rm -f "$WRAPPER_PATH"
	fi

	# ============================================
	# OPTIONAL CONFIG REMOVAL
	# ============================================

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
