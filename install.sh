#!/bin/bash

# Plasma Spotlight Installer
# Safe for curl | bash usage

install_plasma_spotlight() {
	set -e # Exit on any error

	# Configuration
	INSTALL_DIR="$HOME/.local/share/plasma-spotlight"
	BIN_DIR="$HOME/.local/bin"
	REPO_URL="https://github.com/abirkel/plasma-spotlight.git"
	SCRIPT_NAME="plasma-spotlight"

	echo "Installing Plasma Spotlight..."

	# Prerequisites check
	if ! command -v git &>/dev/null; then
		echo "Error: git is not installed."
		exit 1
	fi

	if ! command -v python3 &>/dev/null; then
		echo "Error: python3 is not installed."
		exit 1
	fi

	# Check for KDE Plasma 6 (kwriteconfig6 is required)
	if ! command -v kwriteconfig6 &>/dev/null; then
		echo "Warning: kwriteconfig6 not found. KDE Plasma 6 may not be installed."
		echo "This tool requires KDE Plasma 6 for lock screen integration."

		# Only prompt if running interactively
		if [ -t 0 ]; then
			read -p "Continue anyway? [y/N] " -n 1 -r
			echo
			if [[ ! $REPLY =~ ^[Yy]$ ]]; then
				echo "Installation cancelled."
				exit 1
			fi
		else
			echo "Non-interactive mode: Continuing without kwriteconfig6"
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

		# Only prompt if running interactively
		if [ -t 0 ]; then
			read -r -p "Press Enter to continue with installation..."
			echo ""
		fi
	fi

	# Install Logic
	if [ -f "pyproject.toml" ] && [ -d ".git" ]; then
		echo "Detected local repository. Copying files..."
		mkdir -p "$INSTALL_DIR/plasma_spotlight"

		# Whitelist approach: Copy only what we need
		# This is safer and more explicit than trying to exclude everything we don't want
		cp plasma_spotlight/*.py "$INSTALL_DIR/plasma_spotlight/"
		cp pyproject.toml LICENSE README.md install.sh uninstall.sh "$INSTALL_DIR/"
		
		# Copy thumbnail if it exists
		if [ -f "thumbnail.jpg" ]; then
			cp thumbnail.jpg "$INSTALL_DIR/"
			echo "Copied thumbnail.jpg"
		fi

		echo "Copied application files to $INSTALL_DIR"
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

	cat <<EOF >"$WRAPPER_PATH"
#!/bin/bash
export PYTHONPATH="$INSTALL_DIR:\$PYTHONPATH"
exec python3 -m plasma_spotlight "\$@"
EOF

	chmod +x "$WRAPPER_PATH"

	echo "--------------------------------------------------"
	echo "✓ Success! Installed to: $INSTALL_DIR"
	echo "✓ Executable created at: $WRAPPER_PATH"
	echo ""

	# ============================================
	# USER COMPONENT INSTALLATION (NO SUDO)
	# ============================================

	echo "Installing user components..."

	SYSTEMD_USER_DIR="$HOME/.config/systemd/user"
	SCRIPT_PATH="$BIN_DIR/$SCRIPT_NAME"

	# 1. Create user directories
	mkdir -p "$SYSTEMD_USER_DIR"

	# 2. Install systemd user timer
	echo "Installing systemd user timer..."

	# Write service file
	cat >"$SYSTEMD_USER_DIR/plasma-spotlight.service" <<EOSERVICE
[Unit]
Description=Daily Wallpaper Downloader (Spotlight/Bing)
After=network-online.target suspend.target hibernate.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=$SCRIPT_PATH
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target suspend.target hibernate.target
EOSERVICE

	# Write timer file
	cat >"$SYSTEMD_USER_DIR/plasma-spotlight.timer" <<EOTIMER
[Unit]
Description=Daily Timer for Wallpaper Downloader

[Timer]
# Run at 12:05 AM daily
OnCalendar=*-*-* 00:05:00
# Catch up if system was off
Persistent=true

[Install]
WantedBy=timers.target
EOTIMER

	# Reload systemd and enable timer
	systemctl --user daemon-reload
	if ! systemctl --user enable --now plasma-spotlight.timer; then
		echo "✗ Failed to enable systemd timer"
		exit 1
	fi

	echo "✓ User components installed successfully"

	# ============================================
	# SYSTEM COMPONENT INSTALLATION (REQUIRES SUDO)
	# ============================================

	echo ""
	echo "Installing system components (requires sudo for SDDM theme)..."

	# Run system installation as root
	if sudo bash <<EOSUDO; then
set -e

# Get actual user (not root)
ACTUAL_USER=\${SUDO_USER:-\$USER}
if [ "\$ACTUAL_USER" = "root" ]; then
    echo "Warning: Running as root directly"
    USER_HOME="\$HOME"
else
    USER_HOME=\$(eval echo ~\$ACTUAL_USER)
fi

SDDM_THEME_DIR="/var/sddm_themes/themes/plasma-spotlight"
SDDM_CONF="/etc/sddm.conf.d/plasma-spotlight.conf"
USER_BG_CACHE="/var/cache/plasma-spotlight"
USER_BG_PATH="\$USER_BG_CACHE/current.jpg"

echo "Setting up SDDM theme..."

# 1. Create theme directory
mkdir -p "\$SDDM_THEME_DIR"

# 2. Copy breeze theme as base
if [ -d "/usr/share/sddm/themes/breeze" ]; then
    echo "Copying breeze theme as base..."
    cp -r /usr/share/sddm/themes/breeze/* "\$SDDM_THEME_DIR/"
else
    echo "Warning: Breeze theme not found"
fi

# 3. Create user-writable cache directory for background
mkdir -p "\$USER_BG_CACHE"
chown "\$ACTUAL_USER:\$ACTUAL_USER" "\$USER_BG_CACHE"
chmod 755 "\$USER_BG_CACHE"

# 4. Initialize current.jpg from breeze background if it doesn't exist
if [ -f "/usr/share/sddm/themes/breeze/components/artwork/background.png" ] && [ ! -f "\$USER_BG_PATH" ]; then
    cp /usr/share/sddm/themes/breeze/components/artwork/background.png "\$USER_BG_PATH"
    chown "\$ACTUAL_USER:\$ACTUAL_USER" "\$USER_BG_PATH"
    chmod 644 "\$USER_BG_PATH"
    echo "Initialized current.jpg from breeze background"
fi

# 5. Create theme.conf pointing to cached background
cat > "\$SDDM_THEME_DIR/theme.conf" <<EOTHEME
# Plasma Spotlight SDDM Theme Configuration
[General]
background=\$USER_BG_PATH
EOTHEME

echo "Theme configuration created"

# 5b. Copy thumbnail to theme directory
if [ -f "$INSTALL_DIR/thumbnail.jpg" ]; then
    cp "$INSTALL_DIR/thumbnail.jpg" "\$SDDM_THEME_DIR/thumbnail.jpg"
    echo "Copied theme thumbnail"
fi

# 5c. Update metadata.desktop to give theme a unique name
cat > "\$SDDM_THEME_DIR/metadata.desktop" <<EOMETA
[SddmGreeterTheme]
Name=Plasma Spotlight
Description=Daily wallpaper from Windows Spotlight and Bing
Author=Plasma Spotlight
Copyright=(c) 2024
License=MIT
Type=sddm-theme
Version=0.1
Website=https://github.com/abirkel/plasma-spotlight
Screenshot=thumbnail.jpg
MainScript=Main.qml
ConfigFile=theme.conf
Theme-Id=plasma-spotlight
Theme-API=2.0
QtVersion=6
EOMETA

echo "Theme metadata created"

# 6. Remount overlay to ensure new files are visible
if systemctl is-active --quiet usr-share-sddm-themes.mount; then
    systemctl restart usr-share-sddm-themes.mount
    echo "Remounted SDDM themes overlay"
fi

# 7. Create SDDM config to use our theme
mkdir -p /etc/sddm.conf.d
cat > "\$SDDM_CONF" <<EOCONF
# Plasma Spotlight SDDM Configuration
[Theme]
ThemeDir=/var/sddm_themes/themes
Current=plasma-spotlight
EOCONF

echo "SDDM configuration created"

# 8. Fix SELinux context on cache directory
if command -v restorecon &>/dev/null; then
    restorecon -R "\$USER_BG_CACHE" 2>/dev/null || true
    echo "Fixed SELinux context"
fi

echo "SDDM theme installed successfully"
EOSUDO
		echo "✓ System components installed successfully"
	else
		echo "✗ Failed to install system components"
		exit 1
	fi

	echo ""
	echo "✓ Installation complete!"
	echo "✓ The systemd timer is enabled and will run daily at midnight"
	echo "✓ SDDM theme will be active on the next login screen"
	echo "✓ You can disable the timer with: $SCRIPT_NAME --disable-timer"
	echo "✓ You can enable it again with: $SCRIPT_NAME --enable-timer"
	echo ""

	# Check if ~/.local/bin is in PATH (show message only if not already shown)
	if [[ ":$PATH:" == *":$BIN_DIR:"* ]]; then
		echo "You can now run:"
		echo "  $SCRIPT_NAME          # Download and update wallpapers"
		echo "  $SCRIPT_NAME --help   # Show all options"
	else
		echo "⚠ Remember to add $BIN_DIR to your PATH:"
		echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
		echo ""
		echo "Then restart your terminal or run: source ~/.bashrc"
	fi
	echo "--------------------------------------------------"
}

# Execute the installer (only runs if the full script downloaded)
install_plasma_spotlight "$@"
