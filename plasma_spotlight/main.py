import argparse
import logging
import os
from .config import load_config
from .bing import BingDownloader
from .spotlight import SpotlightDownloader
from .kde import update_lockscreen, setup_sddm_theme, update_user_background, uninstall_sddm_theme, USER_BG_SYMLINK
from .systemd import install_timer, uninstall_timer, enable_timer, disable_timer

def setup_logging():
    """Configure logging with environment variable support for log level."""
    log_level = os.environ.get('PLASMA_SPOTLIGHT_LOG_LEVEL', 'INFO').upper()
    numeric_level = getattr(logging, log_level, logging.INFO)
    
    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
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
    
    parser = argparse.ArgumentParser(description="Daily Wallpaper Downloader for KDE Plasma (Fedora)")
    parser.add_argument("--config", help="Path to configuration file")
    parser.add_argument("--download-only", action="store_true", help="Only download images, do not update wallpaper")
    parser.add_argument("--setup-sddm-theme", action="store_true", help="Setup the custom SDDM theme in /usr/local")
    parser.add_argument("--uninstall-sddm-theme", action="store_true", help="Uninstall the custom SDDM theme")
    parser.add_argument("--update-sddm", action="store_true", help="Update the SDDM wallpaper symlink")
    parser.add_argument("--update-lockscreen", action="store_true", help="Update the KDE lock screen wallpaper")
    
    # Download source selection
    parser.add_argument("--sources", choices=["bing", "spotlight", "both"], help="Which sources to download from")
    parser.add_argument("--spotlight-batch", type=int, choices=[1, 2, 3, 4], help="Number of Spotlight images to request (1-4)")
    
    # Systemd Args
    parser.add_argument("--install-timer", action="store_true", help="Install systemd user service and timer")
    parser.add_argument("--uninstall-timer", action="store_true", help="Uninstall systemd user service and timer")
    parser.add_argument("--enable-timer", action="store_true", help="Enable and start the systemd timer")
    parser.add_argument("--disable-timer", action="store_true", help="Disable and stop the systemd timer")
    
    args = parser.parse_args()
    
    config = load_config(args.config)
    
    # Create effective config by merging CLI args (without mutating original config)
    effective_config = config.copy()
    if args.sources:
        effective_config['download_sources'] = args.sources
    if args.spotlight_batch:
        effective_config['spotlight_batch_count'] = args.spotlight_batch
    
    if args.setup_sddm_theme:
        logger.info("Setting up SDDM Theme structure...")
        return 0 if setup_sddm_theme() else 1
    
    if args.uninstall_sddm_theme:
        logger.info("Uninstalling SDDM Theme...")
        return 0 if uninstall_sddm_theme() else 1
        
    if args.install_timer:
        logger.info("Installing systemd timer...")
        return 0 if install_timer() else 1
        
    if args.enable_timer:
        logger.info("Enabling systemd timer...")
        return 0 if enable_timer() else 1
        
    if args.disable_timer:
        logger.info("Disabling systemd timer...")
        return 0 if disable_timer() else 1
        
    if args.uninstall_timer:
        logger.info("Uninstalling systemd timer...")
        return 0 if uninstall_timer() else 1
    
    # Downloaders
    download_sources = effective_config.get('download_sources', 'both')
    
    bing = BingDownloader(effective_config)
    spotlight = SpotlightDownloader(effective_config)
    
    logger.info("Starting Daily Wallpaper Downloader")
    
    downloaded_bing = []
    downloaded_spotlight = []
    
    if download_sources in ['bing', 'both']:
        downloaded_bing = bing.run()
    else:
        logger.info("Skipping Bing (source not selected)")
    
    if download_sources in ['spotlight', 'both']:
        downloaded_spotlight = spotlight.run()
    else:
        logger.info("Skipping Spotlight (source not selected)")

    if args.download_only:
        logger.info("Download only mode. Exiting.")
        return 0

    # Wallpaper Updates - select image based on preferred source
    preferred_source = effective_config.get('preferred_source', 'spotlight')
    
    latest_image = None
    if preferred_source == 'spotlight' and downloaded_spotlight:
        latest_image = downloaded_spotlight[0]
    elif preferred_source == 'bing' and downloaded_bing:
        latest_image = downloaded_bing[0]
    elif downloaded_spotlight:  # Fallback to spotlight if preferred not available
        latest_image = downloaded_spotlight[0]
    elif downloaded_bing:  # Final fallback to bing
        latest_image = downloaded_bing[0]
        
    if latest_image:
        # Check config or args for update actions
        # CLI flags override config if present (but action=store_true means they are False by default)
        # So we want (arg OR config) is True
        
        do_update_lockscreen = args.update_lockscreen or effective_config.get('update_lockscreen', False)
        do_update_sddm = args.update_sddm or effective_config.get('update_sddm', False)

        if do_update_lockscreen or do_update_sddm:
            # Always update the user symlink first if any update is requested
            logger.info(f"Updating user background symlink to: {latest_image}")
            if update_user_background(latest_image):
                
                if do_update_lockscreen:
                    logger.info("Updating Lock Screen configuration...")
                    if not update_lockscreen(USER_BG_SYMLINK):
                        logger.error("Failed to update lock screen")
                    
                if do_update_sddm:
                    logger.info("SDDM background updated via common symlink.")
            else:
                logger.error("Failed to update user background symlink. Aborting system updates.")
                return 1

    else:
        logger.info("No new images downloaded or found to update system.")
    
    return 0

if __name__ == "__main__":
    main()
