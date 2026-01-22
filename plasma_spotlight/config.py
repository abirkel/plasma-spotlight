import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

DEFAULT_CONFIG: Dict[str, Any] = {
    "save_path_spotlight": str(Path.home() / "Pictures/Wallpapers/Spotlight"),
    "save_path_bing": str(Path.home() / "Pictures/Wallpapers/Bing"),
    "bing_regions": ["ja-JP", "en-US", "en-GB", "intl"],
    "resolution": "UHD",
    "preferred_source": "spotlight",  # or "bing"
    "spotlight_country": "US",
    "spotlight_locale": "en-US",
    "spotlight_batch_count": 1,  # 1-4
    "download_sources": "both",  # "bing", "spotlight", or "both"
}


def validate_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and sanitize configuration values.

    Args:
        config: Configuration dictionary to validate

    Returns:
        Validated configuration dictionary
    """
    # Validate spotlight_batch_count
    if "spotlight_batch_count" in config:
        batch = config["spotlight_batch_count"]
        if not isinstance(batch, int) or batch < 1 or batch > 4:
            logger.warning(f"Invalid spotlight_batch_count: {batch}. Using default: 1")
            config["spotlight_batch_count"] = 1

    # Validate download_sources
    if "download_sources" in config:
        sources = config["download_sources"]
        if sources not in ["bing", "spotlight", "both"]:
            logger.warning(
                f"Invalid download_sources: {sources}. Using default: 'both'"
            )
            config["download_sources"] = "both"

    # Validate preferred_source
    if "preferred_source" in config:
        pref = config["preferred_source"]
        if pref not in ["bing", "spotlight"]:
            logger.warning(
                f"Invalid preferred_source: {pref}. Using default: 'spotlight'"
            )
            config["preferred_source"] = "spotlight"

    # Validate resolution
    if "resolution" in config:
        res = config["resolution"]
        if res not in ["UHD", "1920x1080", "1366x768"]:
            logger.warning(f"Invalid resolution: {res}. Using default: 'UHD'")
            config["resolution"] = "UHD"

    # Validate paths exist or can be created
    for path_key in ["save_path_spotlight", "save_path_bing"]:
        if path_key in config:
            try:
                path = Path(config[path_key]).expanduser()
                config[path_key] = str(path)
            except Exception as e:
                logger.warning(f"Invalid path for {path_key}: {e}. Using default")
                config[path_key] = DEFAULT_CONFIG[path_key]

    return config


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    if config_path:
        path = Path(config_path)
    else:
        path = Path.home() / ".config/plasma-spotlight/config.json"

    if not path.exists():
        return DEFAULT_CONFIG.copy()

    try:
        with open(path, "r") as f:
            user_config = json.load(f)
            # Merge with defaults
            config = DEFAULT_CONFIG.copy()
            config.update(user_config)
            # Validate the merged config
            return validate_config(config)
    except (json.JSONDecodeError, OSError, PermissionError) as e:
        logger.warning(f"Error loading config from {path}: {e}. Using defaults.")
        return DEFAULT_CONFIG.copy()
