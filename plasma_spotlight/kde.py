import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

# User-writable background location (no sudo needed for daily updates)
USER_BG_DIR = Path.home() / ".local/share/plasma-spotlight"
USER_BG_SYMLINK = USER_BG_DIR / "current.jpg"


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
    """Updates the symlink at ~/.local/share/plasma-spotlight/current.jpg

    This is user-level, no sudo needed for daily updates.
    SELinux context is set once during installation, not at runtime.

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
        # Ensure directory exists
        USER_BG_DIR.mkdir(parents=True, exist_ok=True)

        # Remove old symlink if exists (handles both valid and broken symlinks)
        if USER_BG_SYMLINK.exists() or USER_BG_SYMLINK.is_symlink():
            USER_BG_SYMLINK.unlink()

        # Create new symlink
        USER_BG_SYMLINK.symlink_to(image_path_obj.absolute())
        logger.info(f"Updated user background symlink to: {image_path}")

        return True

    except Exception as e:
        logger.error(f"Failed to update user background symlink: {e}")
        return False
