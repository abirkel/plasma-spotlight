import argparse
import logging
from .config import load_config
from .bing import BingDownloader
from .spotlight import SpotlightDownloader
from .kde import update_lockscreen, setup_sddm_theme, update_user_background, uninstall_sddm_theme, USER_BG_SYMLINK
from .systemd import install_timer, uninstall_timer, enable_timer, disable_timer

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
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
    
    # Override config with CLI args if provided
    if args.sources:
        config['download_sources'] = args.sources
    if args.spotlight_batch:
        config['spotlight_batch_count'] = args.spotlight_batch
    
    if args.setup_sddm_theme:
        logger.info("Setting up SDDM Theme structure...")
        setup_sddm_theme()
        return # Exit after setup
    
    if args.uninstall_sddm_theme:
        logger.info("Uninstalling SDDM Theme...")
        uninstall_sddm_theme()
        return # Exit after uninstall
        
    if args.install_timer:
        logger.info("Installing systemd timer...")
        install_timer()
        return # Exit after admin action
        
    if args.enable_timer:
        logger.info("Enabling systemd timer...")
        enable_timer()
        return # Exit after admin action
        
    if args.disable_timer:
        logger.info("Disabling systemd timer...")
        disable_timer()
        return # Exit after admin action
        
    if args.uninstall_timer:
        logger.info("Uninstalling systemd timer...")
        uninstall_timer()
        return # Exit after admin action
    
    # Downloaders
    download_sources = config.get('download_sources', 'both')
    
    bing = BingDownloader(config)
    spotlight = SpotlightDownloader(config)
    
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
        return

    # Wallpaper Updates
    # Logic to select which image to use for lockscreen/sddm could be configurable
    # For now, let's assume we use the latest downloaded image from a preferred source (e.g., Spotlight)
    # This logic needs to be refined based on user preference in config
    
    latest_image = None
    if downloaded_spotlight:
        latest_image = downloaded_spotlight[0] # Assume first is newest/best
    elif downloaded_bing:
        latest_image = downloaded_bing[0]
        
    if latest_image:
        # Check config or args for update actions
        # CLI flags override config if present (but action=store_true means they are False by default)
        # So we want (arg OR config) is True
        
        do_update_lockscreen = args.update_lockscreen or config.get('update_lockscreen', False)
        do_update_sddm = args.update_sddm or config.get('update_sddm', False)

        if do_update_lockscreen or do_update_sddm:
            # Always update the user symlink first if any update is requested
            logger.info(f"Updating user background symlink to: {latest_image}")
            if update_user_background(latest_image):
                
                if do_update_lockscreen:
                    # Use the symlink path for lockscreen to avoid polluting history
                    logger.info("Updating Lock Screen configuration...")
                    # We pass the Absolute Path of the symlink
                    update_lockscreen(USER_BG_SYMLINK)
                    
                if do_update_sddm:
                    logger.info("SDDM background updated via common symlink.")
                    # No extra step needed as SDDM theme points to this symlink
            else:
                logger.error("Failed to update user background symlink. Aborting system updates.")

    else:
        logger.info("No new images downloaded or found to update system.")

if __name__ == "__main__":
    main()
