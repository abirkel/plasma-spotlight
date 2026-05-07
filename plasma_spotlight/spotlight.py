"""
Windows Spotlight image downloader.

Spotlight API v4 endpoint and parameters documented by:
Spotlight Downloader by ORelio (https://github.com/ORelio/Spotlight-Downloader)
Licensed under CDDL-1.0

This implementation is independent and written from scratch.
"""

import logging
import urllib.parse
import json
import datetime
from pathlib import Path
from typing import Optional, List
from .utils import download_file, save_metadata, fetch_json

logger = logging.getLogger(__name__)

# Constants
SPOTLIGHT_API_URL = "https://fd.api.iris.microsoft.com/v4/api/selection"
SPOTLIGHT_USER_AGENT = "Mozilla/5.0"
SPOTLIGHT_PLACEMENT = "88000820"
SPOTLIGHT_MIN_BATCH = 1
SPOTLIGHT_MAX_BATCH = 4


class SpotlightDownloader:
    def __init__(self, config):
        self.config = config
        self.save_path = Path(self.config["save_path_spotlight"])
        self.api_url = SPOTLIGHT_API_URL
        self.user_agent = SPOTLIGHT_USER_AGENT

    def run(self) -> Optional[List[str]]:
        """Download Windows Spotlight wallpapers.

        Returns:
            List of downloaded image paths as strings (empty if no new images),
            or None if download failed
        """
        logger.info("Running Spotlight Downloader...")

        # Configurable batch count (1-4)
        batch_count = self.config.get("spotlight_batch_count", 4)
        batch_count = max(SPOTLIGHT_MIN_BATCH, min(SPOTLIGHT_MAX_BATCH, batch_count))

        params = {
            "placement": SPOTLIGHT_PLACEMENT,
            "bcnt": str(batch_count),
            "country": self.config.get("spotlight_country", "US"),
            "locale": self.config.get("spotlight_locale", "en-US"),
            "fmt": "json",
        }

        headers = {"User-Agent": self.user_agent}

        downloaded_images = []
        total_downloaded = 0

        try:
            # Construct a full URL with params for urllib
            query_string = urllib.parse.urlencode(params)
            full_url = f"{self.api_url}?{query_string}"

            logger.info(f"Requesting {batch_count} Spotlight images")
            data = fetch_json(full_url, headers=headers)
            if not data:
                logger.warning("No data received from Spotlight API")
                return []

            items = data.get("batchrsp", {}).get("items", [])
            logger.info(f"Found {len(items)} items in Spotlight rotation")

            for item_wrapper in items:
                try:
                    # The useful data is inside a JSON string in 'item' field
                    item_json_str = item_wrapper.get("item")
                    if not item_json_str:
                        continue

                    try:
                        item = json.loads(item_json_str)
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse item JSON: {e}")
                        continue

                    ad = item.get("ad", {})

                    # Extract Image URL
                    img_url = ad.get("landscapeImage", {}).get("asset")

                    if not img_url or not isinstance(img_url, str):
                        logger.warning("No landscape image found in item")
                        continue

                    # Filename logic with 5-level fallback
                    url_parts = img_url.split("/")
                    if not url_parts:
                        logger.warning(f"Invalid image URL: {img_url}")
                        continue
                    raw_filename = url_parts[-1]
                    filename = self._get_clean_filename(img_url, ad, raw_filename)

                    full_path = self.save_path / filename

                    if full_path.exists():
                        logger.info(f"Already exists: {filename}")
                        continue

                    # Metadata
                    title = ad.get("title", "No Title")
                    location_subject = ad.get("iconHoverText")
                    desc = ad.get("description", "No Description")
                    copyright = ad.get("copyright", "No Copyright")

                    success = download_file(img_url, full_path)

                    if not success:
                        logger.error(f"{filename}: Download failed - skipping")
                        continue

                    downloaded_images.append(str(full_path))
                    total_downloaded += 1

                    # Prepare metadata
                    meta = {
                        "source": "Spotlight",
                        "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "location_subject": location_subject,
                        "title": title,
                        "description": desc,
                        "copyright": copyright,
                        "url": img_url,
                        "interactive_hotspots": str(
                            [
                                h.get("label")
                                for h in ad.get("relatedHotspots", [])
                                if h.get("label")
                            ]
                        ),
                    }
                    save_metadata(meta, full_path)

                except Exception as e:
                    logger.error(f"Error processing spotlight item: {e}")

        except Exception as e:
            logger.error(f"Spotlight API request failed: {e}")

        if total_downloaded == 0:
            logger.info("No new Spotlight images to download")
        else:
            logger.info(f"Downloaded {total_downloaded} new Spotlight image(s)")

        return downloaded_images

    def _get_clean_filename(self, img_url, ad, raw_filename):
        """
        Extract clean filename with 5-level fallback strategy.

        Level 1: spotlightid from ctaUri (best)
        Level 2: Extract from original filename (good)
        Level 3: Trim to desktop-... (acceptable)
        Level 4: Use title field (fallback for non-desktop files)
        Level 5: Keep vanilla name (last resort)

        Returns: filename string
        """
        import re

        # Extract resolution from URL
        resolution = img_url.split("_")[-1].replace(".jpg", "")  # e.g., "3840x2160"

        # Level 1: Try spotlightid from ctaUri
        cta_uri = ad.get("ctaUri", "")
        if "spotlightid=" in cta_uri:
            try:
                spotlight_id = cta_uri.split("spotlightid=")[1].split("&")[0]

                # Strip prefix if pattern matches: SHORT_ProperName
                if "_" in spotlight_id:
                    parts = spotlight_id.split("_", 1)
                    prefix, name = parts[0], parts[1]

                    # Strip if prefix is short and name starts with capital
                    if len(prefix) <= 4 and name and name[0].isupper():
                        clean_name = name
                    else:
                        clean_name = spotlight_id
                else:
                    clean_name = spotlight_id

                filename = f"{clean_name}_{resolution}.jpg"
                return filename
            except Exception:
                pass

        # Level 2: Try extracting from original filename
        if "desktop-" in raw_filename:
            try:
                # Find start of name
                if "_ds_" in raw_filename:
                    start_idx = raw_filename.find("_ds_") + 4
                else:
                    start_idx = (
                        raw_filename.find("_", raw_filename.find("desktop-")) + 1
                    )

                name_part = raw_filename[start_idx:]

                # First pass: Known sources (fast path)
                known_sources = [
                    "gettyimages",
                    "shutterstock",
                    "adobestock",
                    "estockphoto",
                    "alamy",
                    "pocstock",
                    "designpics",
                    "superstock",
                    "age-",
                ]

                end_idx = len(name_part)
                found_source = False

                for source in known_sources:
                    pos = name_part.find(f"_{source}")
                    if pos != -1 and pos < end_idx:
                        end_idx = pos
                        found_source = True
                        break

                # Second pass: Pattern fallback for unknown sources
                if not found_source:
                    pattern = r"_[a-z][a-z-]*[-_]\d"
                    match = re.search(pattern, name_part)

                    if match:
                        end_idx = match.start()
                        # Log new source detection
                        new_source = (
                            name_part[end_idx + 1 :].split("-")[0].split("_")[0]
                        )
                        logger.info(
                            f"New image source detected: '{new_source}' - consider adding to known_sources list"
                        )

                # Extract clean name
                if end_idx > 0 and end_idx < len(name_part):
                    clean_name = name_part[:end_idx]
                    filename = f"{clean_name}_{resolution}.jpg"
                    logger.debug(f"Filename level 2 (extracted): {filename}")
                    return filename
            except Exception:
                pass

            # Level 3: Trim to desktop-...
            filename = raw_filename[raw_filename.find("desktop-") :]
            logger.debug(f"Filename level 3 (desktop trim): {filename}")
            return filename

        # Level 4: Use title field (for non-desktop files)
        title = ad.get("title", "")
        if title:
            try:
                # Sanitize title: remove special chars, spaces, keep alphanumeric
                safe_title = re.sub(r"[^a-zA-Z0-9]", "", title)
                if safe_title:
                    filename = f"{safe_title}_{resolution}.jpg"
                    logger.debug(f"Filename level 4 (title): {filename}")
                    return filename
            except Exception:
                pass

        # Level 5: Keep vanilla name
        logger.debug(f"Filename level 5 (vanilla): {raw_filename}")
        return raw_filename
