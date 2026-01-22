import logging
import subprocess
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

# User-writable background location (no sudo needed for daily updates)
USER_BG_DIR = Path.home() / ".local/share/plasma-spotlight"
USER_BG_SYMLINK = USER_BG_DIR / "current.jpg"

# System-wide SDDM theme location (needs sudo for setup only)
SDDM_THEME_DIR = Path("/var/lib/sddm/themes/plasma-spotlight")
SDDM_CONF = Path("/etc/sddm.conf.d/plasma-spotlight.conf")
THEME_NAME = "plasma-spotlight"


def run_command(cmd):
    """Run a command safely using list-based arguments.

    Args:
        cmd: List of command arguments (e.g., ['kwriteconfig6', '--file', 'config'])

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except subprocess.CalledProcessError as e:
        logger.error(
            f"Command failed: {' '.join(cmd)}\nError: {e.stderr.decode().strip()}"
        )
        return False


def update_lockscreen(image_path: str) -> bool:
    """Updates the KDE Lock Screen wallpaper using kwriteconfig6.

    Args:
        image_path: Absolute path to the wallpaper image

    Returns:
        bool: True if successful, False otherwise
    """
    # Check if we should use the symlink
    target_path = image_path

    # If the image path is NOT the symlink but we have a valid symlink structure,
    # we might want to encourage using the symlink.
    # However, main.py will pass the raw path, so we should decide here.
    # Actually, main.py should be responsible for updating the symlink FIRST,
    # then passing the symlink path here if desired.

    if not target_path.exists():
        logger.error(f"Image not found for lockscreen: {target_path}")
        return False

    logger.info(f"Setting lockscreen wallpaper to: {target_path}")

    file_uri = Path(target_path).as_uri()
    cmd = [
        "kwriteconfig6",
        "--file",
        "kscreenlockerrc",
        "--group",
        "Greeter",
        "--group",
        "Wallpaper",
        "--group",
        "org.kde.image",
        "--group",
        "General",
        "--key",
        "Image",
        file_uri,
    ]

    return run_command(cmd)


def internal_install() -> bool:
    """Internal installation function called by install.sh.
    
    Sets up SDDM theme, installs and enables systemd timer.
    Handles sudo elevation automatically when needed.

    Returns:
        bool: True if successful, False otherwise
    """
    # Part 1: User-writable setup (no sudo needed)
    logger.info("Creating user background directory...")
    USER_BG_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"Background directory created at: {USER_BG_DIR}")

    # Part 2: System setup (needs sudo)
    import os

    if os.geteuid() != 0:
        logger.info("SDDM theme installation requires elevated privileges.")
        logger.info("Re-running setup with sudo...")

        # Re-execute with sudo using the installed entry point script
        script_path = shutil.which("plasma-spotlight")
        if not script_path:
            logger.error("Could not find plasma-spotlight in PATH")
            return False

        cmd = ["sudo", script_path, "--_internal-install"]

        try:
            subprocess.run(cmd, check=True)
            logger.info("SDDM theme setup complete!")
            
            # Install and enable systemd timer (as user)
            from .systemd import install_timer, enable_timer
            
            logger.info("Installing systemd timer...")
            if not install_timer():
                logger.error("Failed to install systemd timer")
                return False
            
            logger.info("Enabling systemd timer...")
            if not enable_timer():
                logger.error("Failed to enable systemd timer")
                return False
            
            logger.info("Installation complete!")
            logger.info("The systemd timer is enabled and will run daily.")
            logger.info("The theme will be active on the next login screen.")
            return True
        except subprocess.CalledProcessError:
            logger.error("Failed to complete SDDM setup via sudo")
            return False

    # We're root - do system setup
    return _setup_sddm_as_root()


def _setup_sddm_as_root() -> bool:
    """Root-only operations for SDDM theme setup.

    Creates theme directory, copies breeze theme, configures SDDM,
    initializes current.jpg from breeze background, and sets SELinux context.

    Returns:
        bool: True if successful, False otherwise
    """
    import os
    import configparser

    try:
        # Get the actual user (not root)
        actual_user = os.environ.get("SUDO_USER", os.environ.get("USER"))
        if actual_user == "root":
            logger.warning(
                "Running as root directly. Assuming /root as home or continuing..."
            )
            pass

        logger.info("Installing SDDM theme...")

        # 1. Create theme directory
        SDDM_THEME_DIR.mkdir(parents=True, exist_ok=True)

        # 2. Copy breeze theme as base
        breeze_theme = Path("/usr/share/sddm/themes/breeze")
        if breeze_theme.exists():
            logger.info("Copying breeze theme as base...")
            shutil.copytree(breeze_theme, SDDM_THEME_DIR, dirs_exist_ok=True)
        else:
            logger.warning("Breeze theme not found. Creating minimal theme...")

        # 3. Determine user's background path
        if actual_user and actual_user != "root":
            import pwd

            user_home = Path(pwd.getpwnam(actual_user).pw_dir)
            bg_path = user_home / ".local/share/plasma-spotlight/current.jpg"
        else:
            bg_path = USER_BG_DIR / "current.jpg"

        # 4. Initialize current.jpg from breeze background
        if breeze_theme.exists():
            theme_conf = SDDM_THEME_DIR / "theme.conf"
            if theme_conf.exists():
                try:
                    config = configparser.ConfigParser()
                    config.read(theme_conf)
                    
                    if config.has_option('General', 'background'):
                        breeze_bg_path = config.get('General', 'background')
                        breeze_bg = Path(breeze_bg_path)
                        
                        if breeze_bg.exists() and not bg_path.exists():
                            # Copy breeze background as initial current.jpg
                            shutil.copy2(breeze_bg, bg_path)
                            logger.info(f"Initialized current.jpg from breeze background: {breeze_bg}")
                except Exception as e:
                    logger.warning(f"Could not initialize current.jpg from breeze background: {e}")

        # 5. Create theme.conf pointing to user's background
        theme_conf = SDDM_THEME_DIR / "theme.conf"

        with open(theme_conf, "w") as f:
            f.write("# Plasma Spotlight SDDM Theme Configuration\n")
            f.write("[General]\n")
            f.write(f"background={bg_path}\n")

        logger.info(f"Theme configuration created: {theme_conf}")

        # 6. Create SDDM config to use our theme
        SDDM_CONF.parent.mkdir(parents=True, exist_ok=True)

        with open(SDDM_CONF, "w") as f:
            f.write("# Plasma Spotlight SDDM Configuration\n")
            f.write(
                "# This file sets the custom theme directory and activates the theme\n"
            )
            f.write("[Theme]\n")
            f.write("ThemeDir=/var/lib/sddm/themes\n")
            f.write("Current=plasma-spotlight\n")

        logger.info(f"SDDM configuration created: {SDDM_CONF}")

        # 7. Set SELinux context while we're still root
        _set_selinux_context_as_root(actual_user)

        logger.info("SDDM theme installed successfully!")

        return True

    except Exception as e:
        logger.error(f"Failed to setup SDDM theme: {e}")
        return False


def _set_selinux_context_as_root(actual_user: str) -> None:
    """Set SELinux context for user background directory (must be run as root).

    Args:
        actual_user: Username of the actual user (not root)
    """
    # Check if SELinux is installed and enabled
    if not Path("/usr/sbin/selinuxenabled").exists():
        logger.debug("SELinux not installed, skipping context setup")
        return

    try:
        # Check if SELinux is enabled
        result = subprocess.run(
            ["/usr/sbin/selinuxenabled"], check=False, capture_output=False
        )

        if result.returncode != 0:
            logger.debug("SELinux not enabled, skipping context setup")
            return

        # Determine the user's background directory
        if actual_user and actual_user != "root":
            import pwd

            user_home = Path(pwd.getpwnam(actual_user).pw_dir)
            bg_dir = user_home / ".local/share/plasma-spotlight"
        else:
            bg_dir = USER_BG_DIR

        if not bg_dir.exists():
            logger.debug(
                f"Background directory {bg_dir} doesn't exist yet, skipping SELinux context"
            )
            return

        logger.info(f"Setting SELinux context for {bg_dir}...")
        subprocess.run(
            ["chcon", "-R", "-t", "xdm_home_t", str(bg_dir)],
            check=True,
            capture_output=False,
        )

        logger.info("SELinux context set successfully (xdm_home_t)")

    except subprocess.CalledProcessError as e:
        logger.warning(f"Could not set SELinux context: {e}")
        logger.warning("SDDM may not be able to read the background image")
    except FileNotFoundError:
        logger.debug("SELinux tools not found, skipping context setup")


def _set_selinux_context() -> None:
    """Set SELinux context for user background directory (deprecated - kept for compatibility)."""
    # Check if SELinux is installed and enabled
    if not Path("/usr/sbin/selinuxenabled").exists():
        logger.debug("SELinux not installed, skipping context setup")
        return

    try:
        # Check if SELinux is enabled
        result = subprocess.run(
            ["/usr/sbin/selinuxenabled"], check=False, capture_output=False
        )

        if result.returncode != 0:
            logger.debug("SELinux not enabled, skipping context setup")
            return

        logger.info("Setting SELinux context for background directory...")
        subprocess.run(
            ["chcon", "-R", "-t", "xdm_home_t", str(USER_BG_DIR)],
            check=True,
            capture_output=False,
        )

        logger.info("SELinux context set successfully (xdm_home_t)")

    except subprocess.CalledProcessError as e:
        logger.warning(f"Could not set SELinux context: {e}")
        logger.warning("SDDM may not be able to read the background image")
    except FileNotFoundError:
        logger.debug("SELinux tools not found, skipping context setup")


def internal_uninstall() -> bool:
    """Internal uninstallation function called by uninstall.sh.
    
    Uninstalls SDDM theme, disables and uninstalls systemd timer.
    Handles sudo elevation automatically when needed.

    Returns:
        bool: True if successful, False otherwise
    """
    import os

    if os.geteuid() != 0:
        logger.info("SDDM theme uninstall requires elevated privileges.")
        logger.info("Re-running uninstall with sudo...")

        # Re-execute with sudo using the installed entry point script
        script_path = shutil.which("plasma-spotlight")
        if not script_path:
            logger.error("Could not find plasma-spotlight in PATH")
            return False

        cmd = ["sudo", script_path, "--_internal-uninstall"]

        try:
            result = subprocess.run(cmd, check=False)
            if result.returncode != 0:
                logger.error("Failed to uninstall SDDM theme via sudo")
                return False

            # Disable and uninstall systemd timer (as user)
            from .systemd import disable_timer, uninstall_timer
            
            logger.info("Disabling systemd timer...")
            disable_timer()  # Don't fail if already disabled
            
            logger.info("Uninstalling systemd timer...")
            if not uninstall_timer():
                logger.warning("Failed to uninstall systemd timer")

            # Clean up user symlink only (as user)
            if USER_BG_SYMLINK.exists() or USER_BG_SYMLINK.is_symlink():
                logger.info(f"Removing user background symlink: {USER_BG_SYMLINK}")
                try:
                    USER_BG_SYMLINK.unlink()
                except FileNotFoundError:
                    pass  # Already gone

            logger.info("Uninstallation complete!")
            return True
        except Exception as e:
            logger.error(f"Failed to uninstall: {e}")
            return False

    # We're root - do the uninstall
    try:
        if SDDM_THEME_DIR.exists():
            logger.info(f"Removing theme directory: {SDDM_THEME_DIR}")
            shutil.rmtree(SDDM_THEME_DIR)

        if SDDM_CONF.exists():
            logger.info(f"Removing SDDM configuration: {SDDM_CONF}")
            SDDM_CONF.unlink()

        logger.info("System SDDM files removed successfully")
        return True

    except Exception as e:
        logger.error(f"Failed to uninstall SDDM theme: {e}")
        return False


def update_user_background(image_path: str) -> bool:
    """Updates the symlink at ~/.local/share/plasma-spotlight/current.jpg

    This is user-level, no sudo needed for daily updates.

    Args:
        image_path: Absolute path to the wallpaper image

    Returns:
        bool: True if successful, False otherwise
    """
    if not Path(image_path).exists():
        logger.error(f"Image not found: {image_path}")
        return False

    try:
        # Ensure directory exists
        USER_BG_DIR.mkdir(parents=True, exist_ok=True)

        # Remove old symlink if exists (handles both valid and broken symlinks)
        try:
            USER_BG_SYMLINK.unlink()
        except FileNotFoundError:
            pass  # Symlink doesn't exist, that's fine

        # Create new symlink
        USER_BG_SYMLINK.symlink_to(Path(image_path).absolute())
        logger.info(f"Updated user background symlink to: {image_path}")

        return True

    except Exception as e:
        logger.error(f"Failed to update user background symlink: {e}")
        return False
