import urllib.request
import urllib.error
import json
import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

def ensure_directory(path):
    """Ensures the directory exists."""
    Path(path).mkdir(parents=True, exist_ok=True)

def fetch_json(url, headers=None):
    """Fetches JSON data from a URL using urllib."""
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

def check_url_exists(url):
    """Check if a URL exists using HTTP HEAD request."""
    try:
        req = urllib.request.Request(url, method='HEAD')
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

def download_file(url, filepath):
    """Downloads a file from a URL to the specified filepath using urllib."""
    try:
        ensure_directory(str(Path(filepath).parent))
        
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as response:
            with open(filepath, 'wb') as f:
                shutil.copyfileobj(response, f)
                
        logger.info(f"Downloaded: {filepath}")
        return True
    except Exception as e:
        logger.error(f"Failed to download {url}: {e}")
        filepath_obj = Path(filepath)
        if filepath_obj.exists():  # Cleanup partial download
            filepath_obj.unlink()
        return False

def save_metadata(metadata, filepath):
    """Saves metadata dictionary to a text file sidecar next to the image."""
    try:
        with open(filepath, 'w') as f:
            source = metadata.get('source', 'Unknown Source').upper()
            f.write(f"{source} METADATA\n")
            f.write("=" * 20 + "\n")
            
            # Core fields first for consistency
            core_keys = ['date', 'title', 'copyright', 'url']
            for k in core_keys:
                if k in metadata:
                    label = k.replace('_', ' ').title()
                    f.write(f"{label:<16}: {metadata[k]}\n")
            
            # Remaining fields
            exclude_keys = core_keys + ['source', 'filepath']
            for k, v in metadata.items():
                if k not in exclude_keys and v:
                     label = k.replace('_', ' ').title()
                     f.write(f"{label:<16}: {v}\n")

        logger.info(f"Generated sidecar: {filepath}")
        return True
    except Exception as e:
        logger.error(f"Failed to save metadata sidecar {filepath}: {e}")
        return False
