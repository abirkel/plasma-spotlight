import logging
import datetime
from pathlib import Path
from .utils import download_file, save_metadata, fetch_json

logger = logging.getLogger(__name__)

class BingDownloader:
    def __init__(self, config):
        self.config = config
        self.save_path = Path(self.config['save_path_bing'])
        self.regions = self.config.get('bing_regions', ['en-US'])
        self.base_url = "https://www.bing.com"
        self.archive_url = "https://www.bing.com/HPImageArchive.aspx?format=js&idx=0&n=8&mkt={}"

    def run(self):
        logger.info(f"Running Bing Downloader for regions: {self.regions}")
        downloaded_images = []
        processed_base_names = set()
        total_downloaded = 0

        for region in self.regions:
            logger.info(f"Checking region: {region}")
            try:
                url = self.archive_url.format(region)
                data = fetch_json(url)
                if not data:
                    logger.warning(f"No data received from {region}")
                    continue
                
                images = data.get('images', [])
                logger.info(f"Found {len(images)} images for {region}")
                
                for image_data in images:
                    urlbase = image_data.get('urlbase')
                    
                    # Extract base name for deduplication
                    source_id = urlbase.split('id=')[-1]
                    base_name = source_id.split('_')[0]
                    
                    # Deduplication check using base name
                    if base_name in processed_base_names:
                        logger.info(f"Skipping duplicate: {base_name} from {region}")
                        continue
                    processed_base_names.add(base_name)

                    # Build image URL based on resolution
                    if self.config.get('resolution') == 'UHD':
                         image_url = self.base_url + urlbase + "_UHD.jpg"
                    else:
                         image_url = self.base_url + image_data.get('url')

                    # Filename logic: Keep source filename from URL
                    if self.config.get('resolution') == 'UHD':
                        filename = f"{source_id}_UHD.jpg"
                    else:
                        filename = f"{source_id}.jpg"
                    
                    full_path = self.save_path / filename
                    sidecar_path = self.save_path / f"{Path(filename).stem}.txt"

                    if full_path.exists():
                        logger.info(f"Already exists: {filename}")
                        continue
                    
                    # Try downloading UHD, fallback to HD if fails
                    success = download_file(image_url, str(full_path))
                    if not success and self.config.get('resolution') == 'UHD':
                        logger.warning(f"UHD failed for {filename}, trying HD...")
                        image_url = self.base_url + image_data.get('url')
                        success = download_file(image_url, str(full_path))
                    
                    if success:
                        downloaded_images.append(str(full_path))
                        total_downloaded += 1
                        
                        # Prepare metadata
                        meta = {
                            'source': 'Bing',
                            'date': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            'title': image_data.get('title'),
                            'copyright': image_data.get('copyright'),
                            'url': image_url,
                            'region': region,
                            'start_date': image_data.get('startdate')
                        }
                        save_metadata(meta, str(sidecar_path))
            
            except Exception as e:
                logger.error(f"Error fetching Bing images for region {region}: {e}")

        if total_downloaded == 0:
            logger.info("No new Bing images to download")
        else:
            logger.info(f"Downloaded {total_downloaded} new Bing image(s)")
            
        return downloaded_images
