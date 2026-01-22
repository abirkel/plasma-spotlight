import argparse
import logging
import os
from .config import load_config
from .bing import BingDownloader
from .spotlight import SpotlightDownloader
from .kde import (
    update_lockscreen,
    internal_install,
    internal_uninstall,
    update_user_background,
    USER_BG_SYMLINK,
)
from .systemd import install_timer, uninstall_timer, enable_timer, disable_timer


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
    
    # Internal arguments (hidden from help)
    parser.add_argument(
        "--_internal-install",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--_internal-uninstall",
        action="store_true",
        help=argparse.SUPPRESS,
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

    # Use config values directly
    effective_config = config.copy()

    if args._internal_install:
        logger.info("Installing SDDM theme and systemd timer...")
        return 0 if internal_install() else 1

    if args._internal_uninstall:
        logger.info("Uninstalling SDDM theme and systemd timer...")
        return 0 if internal_uninstall() else 1

    if args.enable_timer:
        logger.info("Enabling systemd timer...")
        return 0 if enable_timer() else 1

    if args.disable_timer:
        logger.info("Disabling systemd timer...")
        return 0 if disable_timer() else 1

    # Downloaders
    download_sources = effective_config.get("download_sources", "both")

    bing = BingDownloader(effective_config)
    spotlight = SpotlightDownloader(effective_config)

    logger.info("Starting Daily Wallpaper Downloader")

    downloaded_bing = []
    downloaded_spotlight = []

    if download_sources in ["bing", "both"]:
        downloaded_bing = bing.run()
    else:
        logger.info("Skipping Bing (source not selected)")

    if download_sources in ["spotlight", "both"]:
        downloaded_spotlight = spotlight.run()
    else:
        logger.info("Skipping Spotlight (source not selected)")

    if args.download_only:
        logger.info("Download only mode. Exiting.")
        return 0

    # Wallpaper Updates - select image based on preferred source
    preferred_source = effective_config.get("preferred_source", "spotlight")

    latest_image = None
    if preferred_source == "spotlight" and downloaded_spotlight:
        latest_image = downloaded_spotlight[0]
    elif preferred_source == "bing" and downloaded_bing:
        latest_image = downloaded_bing[0]
    elif downloaded_spotlight:  # Fallback to spotlight if preferred not available
        latest_image = downloaded_spotlight[0]
    elif downloaded_bing:  # Final fallback to bing
        latest_image = downloaded_bing[0]

    if latest_image:
        logger.info(f"Updating wallpapers to: {latest_image}")
        if update_user_background(latest_image):
            logger.info("Updating lock screen configuration...")
            if not update_lockscreen(USER_BG_SYMLINK):
                logger.error("Failed to update lock screen")
                return 1
            logger.info("Wallpapers updated successfully (lock screen + SDDM)")
        else:
            logger.error("Failed to update wallpapers")
            return 1
    else:
        logger.info("No new images downloaded.")

    return 0


if __name__ == "__main__":
    main()
