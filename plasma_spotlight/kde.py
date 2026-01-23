import logging
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

# System-readable, user-writable cache location (no sudo needed for daily updates)
USER_BG_DIR = Path("/var/cache/plasma-spotlight")
USER_BG_PATH = USER_BG_DIR / "current.jpg"


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
    target_path = Path(image_path)

    if not target_path.exists():
        logger.error(f"Image not found for lockscreen: {target_path}")
        return False

    logger.info(f"Setting lockscreen wallpaper to: {target_path}")

    file_uri = target_path.as_uri()
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


def update_user_background(image_path: str) -> bool:
    """Copies wallpaper to /var/cache/plasma-spotlight/current.jpg

    This is user-level, no sudo needed for daily updates.
    Uses copy instead of symlink for robustness.

    Args:
        image_path: Absolute path to the wallpaper image (str or Path)

    Returns:
        bool: True if successful, False otherwise
    """
    image_path_obj = Path(image_path)

    if not image_path_obj.exists():
        logger.error(f"Image not found: {image_path}")
        return False

    try:
        # Ensure directory exists (should already exist from install)
        if not USER_BG_DIR.exists():
            logger.error(f"Cache directory not found: {USER_BG_DIR}")
            logger.error("Please run the installer to set up the cache directory")
            return False

        # Copy image to cache location
        shutil.copy2(image_path_obj, USER_BG_PATH)

        # Ensure file is world-readable for SDDM
        USER_BG_PATH.chmod(0o644)

        logger.info(f"Updated background cache to: {image_path}")

        return True

    except Exception as e:
        logger.error(f"Failed to update background cache: {e}")
        return False
