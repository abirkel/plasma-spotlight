<img src="thumbnail.jpg" alt="Plasma Spotlight" width="240">

# Plasma Spotlight

> Daily wallpaper automation for KDE Plasma on Fedora

A lightweight Python CLI that downloads stunning daily wallpapers from Windows Spotlight and Bing, then automatically sets them as your lock screen and login background. Built for Fedora (including Atomic/Silverblue) with zero external dependencies.

## Why?

Get fresh, high-quality wallpapers every day without lifting a finger. Windows Spotlight and Bing curate beautiful imagery daily—now you can enjoy them on your KDE desktop with full automation.

## Features

- **Dual Sources**: Windows Spotlight (Iris API) + Bing daily images from multiple regions
- **Seamless Integration**: Updates both KDE lock screen and SDDM login background
- **Atomic-Friendly**: Works perfectly on immutable Fedora variants (Silverblue/Kinoite)
- **Set & Forget**: Systemd timer handles daily downloads automatically
- **Rich Metadata**: Saves image details (title, copyright, location) alongside each wallpaper
- **Zero Dependencies**: Pure Python stdlib—no pip packages required

## Quick Start

**Install:**
```bash
curl -fsSL https://raw.githubusercontent.com/abirkel/plasma-spotlight/main/install.sh | bash
```

That's it. The installer sets up everything—SDDM theme, systemd timer, and runs your first wallpaper update. Fresh wallpapers every day, automatically.

## Requirements

- Python 3.10+
- KDE Plasma 6 (uses `kwriteconfig6`)

## Usage

```bash
# Run manually (downloads + updates wallpapers)
plasma-spotlight

# Set a specific image as wallpaper
plasma-spotlight --set-wallpaper /path/to/image.jpg

# Force refresh (ignores daily limit)
plasma-spotlight --refresh

# Check last update time
plasma-spotlight --status

# Download only (no wallpaper updates)
plasma-spotlight --download-only

# Control the daily timer
plasma-spotlight --disable-timer  # Pause daily updates
plasma-spotlight --enable-timer   # Resume daily updates
```

**Automatic Updates:**
- Runs daily at 12:05 AM
- Runs on system boot
- Runs on wake from suspend/hibernate
- Limited to once per day (use `--refresh` to override)

View timer status: `systemctl --user status plasma-spotlight.timer`

## Configuration

Edit `~/.config/plasma-spotlight/config.json`:

```json
{
  "save_path_bing": "~/Pictures/Wallpapers/Bing",
  "save_path_spotlight": "~/Pictures/Wallpapers/Spotlight",
  "bing_regions": ["en-US", "intl"],
  "resolution": "UHD",
  "spotlight_country": "US",
  "spotlight_locale": "en-US",
  "spotlight_batch_count": 1,
  "download_sources": "both",
  "preferred_source": "spotlight"
}
```

**Key Options**:
- `download_sources`: `"both"`, `"bing"`, or `"spotlight"`
- `preferred_source`: Which source to use for wallpaper - `"spotlight"` or `"bing"`
- `resolution`: `"UHD"` (3840x2160), `"1920x1080"`, or `"1366x768"`
- `spotlight_batch_count`: Number of images to fetch (1-4)

### Logging

```bash
# Debug mode
PLASMA_SPOTLIGHT_LOG_LEVEL=DEBUG plasma-spotlight

# Quiet mode
PLASMA_SPOTLIGHT_LOG_LEVEL=ERROR plasma-spotlight
```

## How It Works

1. **Downloads**: Fetches images from Spotlight/Bing APIs to `~/Pictures/Wallpapers/`
2. **Caches**: Copies selected wallpaper to `/var/cache/plasma-spotlight/current.jpg` (user-writable, system-readable)
3. **Integrates**: Updates KDE lock screen config and SDDM theme points to cached image
4. **Metadata**: Saves image details in `metadata/` subfolders

The SDDM theme lives in `/var/sddm_themes/themes/plasma-spotlight/` (one-time sudo setup during install), but daily updates only touch the user-writable cache—perfect for immutable systems like Bazzite.

## Uninstall

```bash
~/.local/share/plasma-spotlight/uninstall.sh
```

Or remotely:
```bash
curl -fsSL https://raw.githubusercontent.com/abirkel/plasma-spotlight/main/uninstall.sh | bash
```

## Acknowledgments

Windows Spotlight API endpoint documentation from [Spotlight Downloader](https://github.com/ORelio/Spotlight-Downloader) by ORelio (CDDL-1.0).

## License

MIT
