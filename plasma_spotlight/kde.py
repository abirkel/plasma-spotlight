import logging
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

# System-readable, user-writable cache location (no sudo needed for daily updates)
USER_BG_DIR = Path("/var/cache/plasma-spotlight")
USER_BG_PATH = USER_BG_DIR / "current.jpg"
STATUS_FILE = USER_BG_DIR / "last_run"


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


def should_run_update() -> bool:
    """Check if we should run update based on last run time.

    Returns:
        bool: True if we should run (last run was not today), False otherwise
    """
    if not STATUS_FILE.exists():
        logger.debug("No status file found, first run")
        return True

    try:
        last_run_str = STATUS_FILE.read_text(encoding="utf-8").strip()
        last_run = datetime.fromisoformat(last_run_str)

        # Ensure timezone-aware comparison
        if last_run.tzinfo is None:
            last_run = last_run.replace(tzinfo=timezone.utc)

        # Use local timezone for date comparison (timer runs at midnight local time)
        now_local = datetime.now().astimezone()
        today = now_local.date()

        # Convert last_run to local timezone for comparison
        last_run_local = last_run.astimezone()
        last_run_date = last_run_local.date()

        if last_run_date == today:
            logger.info(
                f"Already updated today at {last_run_local.strftime('%H:%M:%S')}"
            )
            return False

        logger.debug(f"Last run was {last_run_date}, running update")
        return True

    except (ValueError, OSError, FileNotFoundError, PermissionError) as e:
        logger.warning(f"Could not read status file: {e}, proceeding with update")
        return True


def mark_run_complete() -> bool:
    """Record current timestamp to status file.

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        now = datetime.now(timezone.utc).isoformat()
        STATUS_FILE.write_text(now, encoding="utf-8")
        logger.debug(f"Marked run complete at {now}")
        return True
    except (OSError, PermissionError) as e:
        logger.error(f"Failed to write status file: {e}")
        return False


def get_last_run_time() -> str:
    """Get the last run time in user's local timezone.

    Returns:
        str: Formatted timestamp or error message
    """
    if not STATUS_FILE.exists():
        return "Never run"

    try:
        last_run_str = STATUS_FILE.read_text(encoding="utf-8").strip()
        last_run = datetime.fromisoformat(last_run_str)

        # Ensure timezone-aware
        if last_run.tzinfo is None:
            last_run = last_run.replace(tzinfo=timezone.utc)

        # Convert to local timezone
        last_run_local = last_run.astimezone()
        return last_run_local.strftime("%Y-%m-%d %H:%M:%S %Z")

    except (ValueError, OSError, FileNotFoundError, PermissionError) as e:
        return f"Error reading status: {e}"


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
