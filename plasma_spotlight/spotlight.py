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
from .utils import download_file, save_metadata, fetch_json

logger = logging.getLogger(__name__)

class SpotlightDownloader:
    def __init__(self, config):
        self.config = config
        self.save_path = Path(self.config['save_path_spotlight'])
        self.api_url = "https://fd.api.iris.microsoft.com/v4/api/selection"
        # User agent from script
        self.user_agent = "Mozilla/5.0"
        
    def run(self):
        logger.info("Running Spotlight Downloader...")
        
        # Configurable batch count (1-4)
        batch_count = self.config.get('spotlight_batch_count', 4)
        batch_count = max(1, min(4, batch_count))  # Clamp to 1-4
        
        params = {
            "placement": "88000820",
            "bcnt": str(batch_count),
            "country": self.config.get('spotlight_country', 'US'),
            "locale": self.config.get('spotlight_locale', 'en-US'),
            "fmt": "json"
        }
        
        headers = {
            "User-Agent": self.user_agent
        }
        
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
            
            items = data.get('batchrsp', {}).get('items', [])
            logger.info(f"Found {len(items)} items in Spotlight rotation")
            
            for item_wrapper in items:
                try:
                    # The useful data is inside a JSON string in 'item' field
                    item_json_str = item_wrapper.get('item')
                    if not item_json_str:
                        continue
                        
                    item = json.loads(item_json_str)
                    ad = item.get('ad', {})
                    
                    # Extract Image URL
                    img_url = ad.get('landscapeImage', {}).get('asset')
                    
                    if not img_url:
                        logger.warning("No landscape image found in item")
                        continue
                        
                    # Filename logic
                    raw_filename = img_url.split('/')[-1]
                    if "desktop-" in raw_filename:
                        filename = raw_filename[raw_filename.find("desktop-"):]
                    else:
                        filename = raw_filename
                        
                    full_path = self.save_path / filename
                    sidecar_path = self.save_path / f"{Path(filename).stem}.txt"
                    
                    if full_path.exists():
                        logger.info(f"Already exists: {filename}")
                        continue
                    
                    # Metadata
                    title = ad.get('title', 'No Title')
                    location_subject = ad.get('iconHoverText')
                    desc = ad.get('description', 'No Description')
                    copyright = ad.get('copyright', 'No Copyright')
                    
                    success = download_file(img_url, str(full_path))
                    
                    if success:
                        downloaded_images.append(str(full_path))
                        total_downloaded += 1
                        
                        # Prepare metadata
                        meta = {
                            'source': 'Spotlight',
                            'date': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            'location_subject': location_subject,
                            'title': title,
                            'description': desc,
                            'copyright': copyright,
                            'url': img_url,
                            'interactive_hotspots': str([h.get('label') for h in ad.get('relatedHotspots', []) if h.get('label')]),
                        }
                        save_metadata(meta, str(sidecar_path))
                        
                except Exception as e:
                    logger.error(f"Error processing spotlight item: {e}")
                    
        except Exception as e:
            logger.error(f"Spotlight API request failed: {e}")
        
        if total_downloaded == 0:
            logger.info("No new Spotlight images to download")
        else:
            logger.info(f"Downloaded {total_downloaded} new Spotlight image(s)")
            
        return downloaded_images
