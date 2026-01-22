import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    "save_path_spotlight": str(Path.home() / "Pictures/Wallpapers/Spotlight"),
    "save_path_bing": str(Path.home() / "Pictures/Wallpapers/Bing"),
    "bing_regions": ["en-US", "ja-JP", "intl"],
    "resolution": "UHD",
    "preferred_source": "spotlight", # or "bing"
    "spotlight_country": "US",
    "spotlight_locale": "en-US",
    "spotlight_batch_count": 1,  # 1-4
    "download_sources": "both",  # "bing", "spotlight", or "both"
    "update_lockscreen": False,
    "update_sddm": False
}

def load_config(config_path=None):
    if config_path:
        path = Path(config_path)
    else:
        path = Path.home() / ".config/plasma-spotlight/config.json"
    
    if not path.exists():
        return DEFAULT_CONFIG
    
    try:
        with open(path, 'r') as f:
            user_config = json.load(f)
            # Merge with defaults
            config = DEFAULT_CONFIG.copy()
            config.update(user_config)
            return config
    except (json.JSONDecodeError, OSError, PermissionError) as e:
        logger.warning(f"Error loading config from {path}: {e}. Using defaults.")
        return DEFAULT_CONFIG
