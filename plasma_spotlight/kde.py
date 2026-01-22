import logging
import subprocess
import os
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
        logger.error(f"Command failed: {' '.join(cmd)}\nError: {e.stderr.decode().strip()}")
        return False

def update_lockscreen(image_path):
    """
    Updates the KDE Lock Screen wallpaper using kwriteconfig6.
    This is user-level, no sudo needed.
    """
    # Check if we should use the symlink
    target_path = image_path
    
    # If the image path is NOT the symlink but we have a valid symlink structure,
    # we might want to encourage using the symlink.
    # However, main.py will pass the raw path, so we should decide here.
    # Actually, main.py should be responsible for updating the symlink FIRST,
    # then passing the symlink path here if desired.
    
    if not os.path.exists(target_path):
        logger.error(f"Image not found for lockscreen: {target_path}")
        return False

    logger.info(f"Setting lockscreen wallpaper to: {target_path}")
    
    file_uri = Path(target_path).as_uri()
    cmd = [
        "kwriteconfig6",
        "--file", "kscreenlockerrc",
        "--group", "Greeter",
        "--group", "Wallpaper",
        "--group", "org.kde.image",
        "--group", "General",
        "--key", "Image",
        file_uri
    ]
    
    return run_command(cmd)

def setup_sddm_theme():
    """
    Sets up SDDM theme for Fedora Atomic.
    Handles sudo elevation automatically.
    """
    # Part 1: User-writable setup (no sudo needed)
    logger.info("Creating user background directory...")
    USER_BG_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"Background directory created at: {USER_BG_DIR}")
    
    # Part 2: System setup (needs sudo)
    if os.geteuid() != 0:
        logger.info("SDDM theme installation requires elevated privileges.")
        logger.info("Re-running setup with sudo...")
        
        # Re-execute with sudo
        import sys
        # Use sys.argv[0] to get the actual invoked script
        script_path = sys.argv[0]
        cmd = ["sudo", "-E", sys.executable, script_path, "--setup-sddm-theme"]
        
        try:
            subprocess.run(cmd, check=True)
            # Part 3: SELinux context (back as user)
            _set_selinux_context()
            logger.info("SDDM theme setup complete!")
            logger.info("The theme will be active on the next login screen.")
            return True
        except subprocess.CalledProcessError:
            logger.error("Failed to complete SDDM setup via sudo")
            return False
    
    # We're root - do system setup
    return _setup_sddm_as_root()

def _setup_sddm_as_root():
    """Root-only operations for SDDM theme setup."""
    try:
        # Get the actual user (not root)
        actual_user = os.environ.get('SUDO_USER', os.environ.get('USER'))
        if actual_user == 'root':
            logger.warning("Running as root directly. Assuming /root as home or continuing...")
            pass
        
        logger.info(f"Installing SDDM theme...")
        
        # 1. Create theme directory
        SDDM_THEME_DIR.mkdir(parents=True, exist_ok=True)
        
        # 2. Copy breeze theme as base
        breeze_theme = Path("/usr/share/sddm/themes/breeze")
        if breeze_theme.exists():
            logger.info("Copying breeze theme as base...")
            shutil.copytree(breeze_theme, SDDM_THEME_DIR, dirs_exist_ok=True)
        else:
            logger.warning("Breeze theme not found. Creating minimal theme...")
        
        # 3. Create theme.conf pointing to user's background
        if actual_user and actual_user != 'root':
             import pwd
             user_home = Path(pwd.getpwnam(actual_user).pw_dir)
             bg_path = user_home / ".local/share/plasma-spotlight/current.jpg"
        else:
             bg_path = USER_BG_DIR / "current.jpg"

        theme_conf = SDDM_THEME_DIR / "theme.conf"
        
        with open(theme_conf, 'w') as f:
            f.write("# Plasma Spotlight SDDM Theme Configuration\n")
            f.write("[General]\n")
            f.write(f"background={bg_path}\n")
        
        logger.info(f"Theme configuration created: {theme_conf}")
        
        # 4. Create SDDM config to use our theme
        SDDM_CONF.parent.mkdir(parents=True, exist_ok=True)
        
        with open(SDDM_CONF, 'w') as f:
            f.write("# Plasma Spotlight SDDM Configuration\n")
            f.write("# This file sets the custom theme directory and activates the theme\n")
            f.write("[Theme]\n")
            f.write("ThemeDir=/var/lib/sddm/themes\n")
            f.write("Current=plasma-spotlight\n")
        
        logger.info(f"SDDM configuration created: {SDDM_CONF}")
        logger.info("SDDM theme installed successfully!")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to setup SDDM theme: {e}")
        return False

def _set_selinux_context():
    """Set SELinux context for user background directory."""
    # Check if SELinux is installed and enabled
    if not Path("/usr/sbin/selinuxenabled").exists():
        logger.debug("SELinux not installed, skipping context setup")
        return
    
    try:
        # Check if SELinux is enabled
        result = subprocess.run(
            ["/usr/sbin/selinuxenabled"],
            check=False,
            capture_output=False
        )
        
        if result.returncode != 0:
            logger.debug("SELinux not enabled, skipping context setup")
            return
        
        logger.info("Setting SELinux context for background directory...")
        subprocess.run(
            ["chcon", "-R", "-t", "xdm_home_t", str(USER_BG_DIR)],
            check=True,
            capture_output=False
        )
        
        logger.info("SELinux context set successfully (xdm_home_t)")
        
    except subprocess.CalledProcessError as e:
        logger.warning(f"Could not set SELinux context: {e}")
        logger.warning("SDDM may not be able to read the background image")
    except FileNotFoundError:
        logger.debug("SELinux tools not found, skipping context setup")

def uninstall_sddm_theme():
    """
    Uninstalls the SDDM theme completely.
    Handles sudo elevation automatically.
    """
    if os.geteuid() != 0:
        logger.info("SDDM theme uninstall requires elevated privileges.")
        logger.info("Re-running uninstall with sudo...")
        
        import sys
        # Use sys.argv[0] to get the actual invoked script
        script_path = sys.argv[0]
        cmd = ["sudo", "-E", sys.executable, script_path, "--uninstall-sddm-theme"]
        
        try:
            result = subprocess.run(cmd, check=False)
            if result.returncode != 0:
                 logger.error("Failed to uninstall SDDM theme via sudo")
                 return False
            
            # Clean up user directory (as user)
            if USER_BG_DIR.exists():
                logger.info(f"Removing user background directory: {USER_BG_DIR}")
                shutil.rmtree(USER_BG_DIR)
            
            logger.info("SDDM theme uninstalled successfully!")
            return True
        except Exception as e:
            logger.error(f"Failed to uninstall SDDM theme: {e}")
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

def update_user_background(image_path):
    """
    Updates the symlink at ~/.local/share/plasma-spotlight/current.jpg
    This is user-level, no sudo needed for daily updates!
    """
    if not os.path.exists(image_path):
        logger.error(f"Image not found: {image_path}")
        return False
    
    try:
        # Ensure directory exists
        USER_BG_DIR.mkdir(parents=True, exist_ok=True)
        
        # Remove old symlink if exists (handles both valid and broken symlinks)
        if USER_BG_SYMLINK.is_symlink() or USER_BG_SYMLINK.exists():
            USER_BG_SYMLINK.unlink()
        
        # Create new symlink
        USER_BG_SYMLINK.symlink_to(Path(image_path).absolute())
        logger.info(f"Updated user background symlink to: {image_path}")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to update user background symlink: {e}")
        return False
