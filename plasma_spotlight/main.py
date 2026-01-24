import argparse
import logging
import os
import socket
import time
from pathlib import Path
from typing import Optional, List
from .config import load_config
from .bing import BingDownloader
from .spotlight import SpotlightDownloader
from .kde import (
    update_lockscreen,
    update_user_background,
    should_run_update,
    mark_run_complete,
    get_last_run_time,
    USER_BG_PATH,
)
from .systemd import enable_timer, disable_timer


def setup_logging():
    """Configure logging with environment variable support for log level."""
    log_level = os.environ.get("PLASMA_SPOTLIGHT_LOG_LEVEL", "INFO").upper()
    numeric_level = getattr(logging, log_level, logging.INFO)

    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


logger = logging.getLogger(__name__)


def wait_for_network_ready(max_wait: float = 5.0, check_interval: float = 0.3) -> bool:
    """Wait for network to be ready with quick retry checks.

    Performs DNS lookups at regular intervals to detect when network is available.
    Useful after system wake from suspend when network may not be immediately ready.

    Args:
        max_wait: Maximum seconds to wait before giving up (default 5.0)
        check_interval: Seconds between network checks (default 0.3)

    Returns:
        bool: True if network is ready, False if timeout reached
    """
    attempts = int(max_wait / check_interval)

    for i in range(attempts):
        try:
            # Quick DNS lookup test to verify network connectivity
            socket.getaddrinfo("www.bing.com", 80, socket.AF_UNSPEC, socket.SOCK_STREAM)
            if i > 0:  # Only log if we had to wait
                logger.info(f"Network ready after {i * check_interval:.1f}s")
            return True
        except socket.gaierror:
            if i == 0:
                logger.debug("Network not immediately ready, waiting...")
            time.sleep(check_interval)

    logger.warning(f"Network not ready after {max_wait}s, proceeding anyway")
    return False


def main() -> int:
    """Main entry point for plasma-spotlight application.

    Handles command-line arguments and orchestrates wallpaper downloads
    and system updates for KDE Plasma lock screen and SDDM.

    Returns:
        int: Exit code (0 for success, 1 for failure)
    """
    setup_logging()

    parser = argparse.ArgumentParser(
        description="Daily Wallpaper Downloader for KDE Plasma (Fedora)"
    )
    parser.add_argument(
        "--download-only",
        action="store_true",
        help="Only download images, do not update wallpaper",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Force wallpaper refresh, ignoring daily limit",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show last update time and exit",
    )
    parser.add_argument(
        "--set-wallpaper",
        type=str,
        metavar="PATH",
        help="Manually set a specific image as lockscreen/SDDM wallpaper",
    )

    # Systemd timer control
    parser.add_argument(
        "--enable-timer", action="store_true", help="Enable and start the systemd timer"
    )
    parser.add_argument(
        "--disable-timer",
        action="store_true",
        help="Disable and stop the systemd timer",
    )

    args = parser.parse_args()

    config = load_config()

    if args.status:
        last_run = get_last_run_time()
        print(f"Last wallpaper update: {last_run}")
        return 0

    if args.enable_timer:
        logger.info("Enabling systemd timer...")
        return 0 if enable_timer() else 1

    if args.disable_timer:
        logger.info("Disabling systemd timer...")
        return 0 if disable_timer() else 1

    # Handle manual wallpaper setting
    if args.set_wallpaper:
        return _handle_set_wallpaper(args.set_wallpaper)

    # Check if we should run (unless --refresh or --download-only)
    if not args.refresh and not args.download_only:
        if not should_run_update():
            logger.info(
                "Wallpaper already updated today. Use --refresh to force update."
            )
            logger.info("Exiting: Daily limit reached")
            return 0

    if args.refresh:
        logger.info("Running with --refresh flag (ignoring daily limit)")

    # Wait for network to be ready (important after wake from suspend)
    wait_for_network_ready()

    # Downloaders
    download_sources = config.get("download_sources", "both")
    preferred_source = config.get("preferred_source", "spotlight")

    bing = BingDownloader(config)
    spotlight = SpotlightDownloader(config)

    logger.info("Starting Daily Wallpaper Downloader")

    downloaded_bing: Optional[List[str]] = None
    downloaded_spotlight: Optional[List[str]] = None
    bing_failed = False
    spotlight_failed = False

    # Download from configured sources
    if download_sources in ["bing", "both"]:
        result = bing.run()
        if result is None:
            bing_failed = True
            logger.error("Bing download encountered a critical error")
        else:
            downloaded_bing = result
            if len(result) == 0:
                logger.debug("Bing: No new images available")
    else:
        logger.info("Skipping Bing (source not selected)")

    if download_sources in ["spotlight", "both"]:
        result = spotlight.run()
        if result is None:
            spotlight_failed = True
            logger.error("Spotlight download encountered a critical error")
        else:
            downloaded_spotlight = result
            if len(result) == 0:
                logger.debug("Spotlight: No new images available")
    else:
        logger.info("Skipping Spotlight (source not selected)")

    # Check for actual failures (not just no new images)
    if bing_failed or spotlight_failed:
        failed_sources = []
        if bing_failed:
            failed_sources.append("Bing")
        if spotlight_failed:
            failed_sources.append("Spotlight")
        logger.error(f"Critical download failure from: {', '.join(failed_sources)}")
        return 1

    if args.download_only:
        logger.info("Download only mode. Exiting.")
        return 0

    # Select image based on preferred source and what was actually downloaded
    latest_image_path = _select_wallpaper_image(
        preferred_source, download_sources, downloaded_spotlight, downloaded_bing
    )

    if latest_image_path:
        logger.info(f"Updating wallpapers to: {latest_image_path}")
        if not update_user_background(latest_image_path):
            logger.error("Failed to update user background cache")
            return 1

        logger.info("Updating lock screen configuration...")
        if not update_lockscreen(str(USER_BG_PATH)):
            logger.error("Failed to update lock screen")
            return 1

        logger.info("Wallpapers updated successfully (lock screen + SDDM)")
        logger.info(f"Active wallpaper: {Path(latest_image_path).name}")

        # Mark run as complete
        if not mark_run_complete():
            logger.warning("Failed to update status file, but wallpaper was updated")
    else:
        logger.info("No new images downloaded. Wallpaper unchanged.")
        logger.info("Exiting: No updates available")

    return 0


def _handle_set_wallpaper(wallpaper_path: str) -> int:
    """Handle manual wallpaper setting via --set-wallpaper.

    Args:
        wallpaper_path: Path to the image file (string)

    Returns:
        int: Exit code (0 for success, 1 for failure)
    """
    # Resolve to absolute path
    wallpaper_path_obj = Path(wallpaper_path).resolve()

    # Validate file exists
    if not wallpaper_path_obj.exists():
        logger.error(f"Image not found: {wallpaper_path_obj}")
        return 1

    if not wallpaper_path_obj.is_file():
        logger.error(f"Path is not a file: {wallpaper_path_obj}")
        return 1

    # Optional: Validate image format
    valid_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    if wallpaper_path_obj.suffix.lower() not in valid_extensions:
        logger.warning(
            f"File extension '{wallpaper_path_obj.suffix}' may not be a valid image format"
        )
        logger.warning("Supported formats: JPG, PNG, BMP, WebP")

    # Update the cache and lockscreen
    logger.info(f"Setting wallpaper to: {wallpaper_path_obj}")

    if not update_user_background(str(wallpaper_path_obj)):
        logger.error("Failed to update user background cache")
        return 1

    logger.info("Updating lock screen configuration...")
    if not update_lockscreen(str(USER_BG_PATH)):
        logger.error("Failed to update lock screen")
        return 1

    logger.info("Wallpaper updated successfully (lock screen + SDDM)")
    logger.info("Note: Systemd timer will override this on next scheduled run")

    # Intentionally NOT calling mark_run_complete() so timer still runs on schedule
    return 0


def _select_wallpaper_image(
    preferred_source: str,
    download_sources: str,
    downloaded_spotlight: Optional[List[str]],
    downloaded_bing: Optional[List[str]],
) -> Optional[str]:
    """Select the wallpaper image based on preferences and what was downloaded.

    Args:
        preferred_source: User's preferred source ("spotlight" or "bing")
        download_sources: Which sources are enabled ("spotlight", "bing", or "both")
        downloaded_spotlight: List of downloaded spotlight image paths (or empty list)
        downloaded_bing: List of downloaded bing image paths (or empty list)

    Returns:
        Path string to selected image, or None if no images available
    """
    # Only consider sources that were actually enabled
    spotlight_available = (
        download_sources in ["spotlight", "both"]
        and downloaded_spotlight is not None
        and len(downloaded_spotlight) > 0
    )
    bing_available = (
        download_sources in ["bing", "both"]
        and downloaded_bing is not None
        and len(downloaded_bing) > 0
    )

    # Try preferred source first
    if preferred_source == "spotlight" and spotlight_available:
        return downloaded_spotlight[0]
    elif preferred_source == "bing" and bing_available:
        return downloaded_bing[0]

    # Fallback to any available source
    if spotlight_available:
        return downloaded_spotlight[0]
    elif bing_available:
        return downloaded_bing[0]

    return None


if __name__ == "__main__":
    main()
