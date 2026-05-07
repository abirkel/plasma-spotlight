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

	# Check for KDE Plasma 6 (kwriteconfig6 is required for lock screen)
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

	# Check for Plasma Login Manager
	if ! systemctl list-unit-files plasmalogin.service &>/dev/null || \
	   ! systemctl list-unit-files plasmalogin.service | grep -q plasmalogin; then
		echo ""
		echo "⚠ Warning: Plasma Login Manager (plasmalogin.service) was not detected."
		echo "  This tool requires plasma-login-manager (included in KDE Plasma 6.6+)."
		echo "  Install it with: sudo dnf install plasma-login-manager"
		echo "  The login screen wallpaper will not update until PLM is installed."
		echo ""
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

		# Allowlist approach: Copy only what we need
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
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=$SCRIPT_PATH
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
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
	echo "Installing system components (requires sudo)..."

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

USER_BG_CACHE="/var/cache/plasma-spotlight"
USER_BG_PATH="\$USER_BG_CACHE/current.jpg"
PLM_CONF="/etc/plasmalogin.conf"

# 1. Create user-writable cache directory for background
mkdir -p "\$USER_BG_CACHE"
chown "\$ACTUAL_USER:\$ACTUAL_USER" "\$USER_BG_CACHE"
chmod 755 "\$USER_BG_CACHE"
echo "Created background cache: \$USER_BG_CACHE"

# 2. Initialize current.jpg from a system wallpaper if it doesn't exist
if [ ! -f "\$USER_BG_PATH" ]; then
    INIT_BG=""
    # Try common system wallpaper locations in order of preference
    for candidate in \
        /usr/share/wallpapers/Next/contents/images/3840x2160.png \
        /usr/share/wallpapers/Next/contents/images/1920x1080.png \
        /usr/share/backgrounds/default.png \
        /usr/share/backgrounds/default.jpg \
        \$(find /usr/share/wallpapers /usr/share/backgrounds -maxdepth 4 \
            \( -name "*.jpg" -o -name "*.png" \) 2>/dev/null | head -1); do
        if [ -f "\$candidate" ]; then
            INIT_BG="\$candidate"
            break
        fi
    done

    if [ -n "\$INIT_BG" ]; then
        cp "\$INIT_BG" "\$USER_BG_PATH"
        chown "\$ACTUAL_USER:\$ACTUAL_USER" "\$USER_BG_PATH"
        chmod 644 "\$USER_BG_PATH"
        echo "Initialized current.jpg from: \$INIT_BG"
    else
        echo "Warning: No system wallpaper found to initialize current.jpg"
        echo "The login screen will use its default background until the first run."
    fi
fi

# 3. Write Plasma Login Manager config
echo "Configuring Plasma Login Manager..."
PLM_IMAGE_URI="file://\$USER_BG_PATH"

# Write the wallpaper config block using Python for reliable INI handling
python3 - <<EOPY
import configparser, sys

conf_path = "\$PLM_CONF"
section = "Greeter][Wallpaper][org.kde.image][General"
key = "Image"
value = "\$PLM_IMAGE_URI"

config = configparser.RawConfigParser()
config.optionxform = str  # Preserve key case

try:
    config.read(conf_path, encoding="utf-8")
except Exception:
    pass  # Start fresh if unreadable

if section not in config:
    config[section] = {}
config[section][key] = value

with open(conf_path, "w", encoding="utf-8") as f:
    config.write(f)

print(f"Plasma Login Manager config written: {conf_path}")
EOPY

# 4. Fix SELinux context on cache directory
if command -v restorecon &>/dev/null; then
    restorecon -R "\$USER_BG_CACHE" 2>/dev/null || true
    echo "Fixed SELinux context"
fi

echo "System components installed successfully"
EOSUDO
		echo "✓ System components installed successfully"
	else
		echo "✗ Failed to install system components"
		exit 1
	fi

	echo ""
	echo "✓ Installation complete!"
	echo "✓ The systemd timer is enabled and will run daily at midnight"
	echo "✓ Timer will catch up on wake if system was asleep at midnight"
	echo "✓ Plasma Login Manager configured — login screen updates on next run"
	echo ""
	echo "Timer control:"
	echo "  $SCRIPT_NAME --disable-timer  # Pause automatic updates"
	echo "  $SCRIPT_NAME --enable-timer   # Resume automatic updates"
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
