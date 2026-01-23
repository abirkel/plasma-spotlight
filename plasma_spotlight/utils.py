import urllib.request
import urllib.error
import json
import logging
import shutil
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def ensure_directory(path) -> None:
    """Ensures the directory exists.

    Args:
        path: Directory path (str or Path) to create
    """
    Path(path).mkdir(parents=True, exist_ok=True)


def fetch_json(url, headers=None) -> Optional[dict]:
    """Fetches JSON data from a URL using urllib.

    Args:
        url: URL to fetch JSON from
        headers: Optional HTTP headers

    Returns:
        Parsed JSON data as dict, or None if failed
    """
    try:
        req = urllib.request.Request(url, headers=headers or {})
        with urllib.request.urlopen(req) as response:
            data = response.read()
            return json.loads(data)
    except urllib.error.URLError as e:
        logger.error(f"Failed to fetch JSON from {url}: {e}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode JSON from {url}: {e}")
        return None


def check_url_exists(url) -> bool:
    """Check if a URL exists using HTTP HEAD request.

    Args:
        url: URL to check

    Returns:
        bool: True if URL exists (200 status), False otherwise
    """
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req) as response:
            return response.status == 200
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return False
        logger.warning(f"HTTP error checking URL {url}: {e.code}")
        return False
    except Exception as e:
        logger.warning(f"Error checking URL {url}: {e}")
        return False


def download_file(url, filepath) -> bool:
    """Downloads a file from a URL to the specified filepath using urllib.

    Args:
        url: URL to download from
        filepath: Destination file path (str or Path)

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        filepath_obj = Path(filepath)
        ensure_directory(filepath_obj.parent)

        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as response:
            with open(filepath_obj, "wb") as f:
                shutil.copyfileobj(response, f)

        logger.info(f"Downloaded: {filepath_obj}")
        return True
    except Exception as e:
        logger.error(f"Failed to download {url}: {e}")
        filepath_obj = Path(filepath)
        if filepath_obj.exists():  # Cleanup partial download
            filepath_obj.unlink()
        return False


def save_metadata(metadata, filepath):
    """Saves metadata dictionary to a text file in the metadata subfolder.

    Args:
        metadata: Dictionary containing image metadata
        filepath: Path to the image file (str or Path)

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Save to metadata subfolder instead of next to image
        filepath_obj = Path(filepath)
        metadata_dir = filepath_obj.parent / "metadata"
        ensure_directory(metadata_dir)

        # Sanitize filename to prevent path traversal
        safe_stem = (
            filepath_obj.stem.replace("..", "").replace("/", "_").replace("\\", "_")
        )
        metadata_filepath = metadata_dir / f"{safe_stem}.txt"

        with open(metadata_filepath, "w") as f:
            source = metadata.get("source", "Unknown Source").upper()
            f.write(f"{source} METADATA\n")
            f.write("=" * 20 + "\n")

            # Core fields first for consistency
            core_keys = ["date", "title", "copyright", "url"]
            for k in core_keys:
                if k in metadata:
                    label = k.replace("_", " ").title()
                    f.write(f"{label:<16}: {metadata[k]}\n")

            # Remaining fields
            exclude_keys = core_keys + ["source", "filepath"]
            for k, v in metadata.items():
                if k not in exclude_keys and v:
                    label = k.replace("_", " ").title()
                    f.write(f"{label:<16}: {v}\n")

        logger.info(f"Generated metadata: {metadata_filepath}")
        return True
    except Exception as e:
        logger.error(f"Failed to save metadata {filepath}: {e}")
        return False
