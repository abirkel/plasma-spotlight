import logging
import datetime
from pathlib import Path
from .utils import download_file, save_metadata, fetch_json, check_url_exists

logger = logging.getLogger(__name__)


class BingDownloader:
    def __init__(self, config):
        self.config = config
        self.save_path = Path(self.config["save_path_bing"])
        self.regions = self.config.get("bing_regions", ["en-US"])
        self.base_url = "https://www.bing.com"
        self.archive_url = (
            "https://www.bing.com/HPImageArchive.aspx?format=js&idx=0&n=8&mkt={}"
        )

    def run(self):
        logger.info(f"Running Bing Downloader for regions: {self.regions}")
        downloaded_images = []
        total_downloaded = 0

        for region in self.regions:
            logger.info(f"Checking region: {region}")
            try:
                url = self.archive_url.format(region)
                data = fetch_json(url)
                if not data:
                    logger.warning(f"No data received from {region}")
                    continue

                images = data.get("images", [])
                logger.info(f"Found {len(images)} images for {region}")

                for image_data in images:
                    urlbase = image_data.get("urlbase")

                    # Extract clean image name (remove OHR. prefix and region/ID suffix)
                    source_id = urlbase.split("id=")[-1]
                    base_name = source_id.split("_")[0].replace("OHR.", "")

                    # Build image URL based on resolution
                    if self.config.get("resolution") == "UHD":
                        image_url = self.base_url + urlbase + "_UHD.jpg"
                    else:
                        image_url = self.base_url + image_data.get("url")

                    # Filename logic: Clean name with resolution
                    if self.config.get("resolution") == "UHD":
                        filename = f"{base_name}_UHD.jpg"
                    else:
                        filename = f"{base_name}.jpg"

                    full_path = self.save_path / filename

                    if full_path.exists():
                        logger.info(f"Already exists: {filename}")
                        continue

                    # Check if the desired resolution exists before attempting download
                    if not check_url_exists(image_url):
                        logger.info(
                            f"{base_name}: {self.config.get('resolution', 'default')} resolution not available - skipping"
                        )
                        continue

                    # Download image in desired resolution
                    success = download_file(image_url, str(full_path))

                    if not success:
                        logger.error(f"{base_name}: Download failed - skipping")
                        continue

                    downloaded_images.append(str(full_path))
                    total_downloaded += 1

                    # Prepare metadata
                    meta = {
                        "source": "Bing",
                        "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "title": image_data.get("title"),
                        "copyright": image_data.get("copyright"),
                        "url": image_url,
                        "region": region,
                        "start_date": image_data.get("startdate"),
                    }
                    save_metadata(meta, str(full_path))

            except Exception as e:
                logger.error(f"Error fetching Bing images for region {region}: {e}")

        if total_downloaded == 0:
            logger.info("No new Bing images to download")
        else:
            logger.info(f"Downloaded {total_downloaded} new Bing image(s)")

        return downloaded_images
