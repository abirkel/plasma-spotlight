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

**Install and run:**
```bash
curl -fsSL https://raw.githubusercontent.com/abirkel/plasma-spotlight/main/install.sh | bash
plasma-spotlight --update-lockscreen --update-sddm
```

**Enable daily automation:**
```bash
plasma-spotlight --install-timer
plasma-spotlight --enable-timer
```

That's it. Fresh wallpapers every day.

## Requirements

- Python 3.10+
- KDE Plasma 6 (uses `kwriteconfig6`)

## Installation

### Automated
```bash
curl -fsSL https://raw.githubusercontent.com/abirkel/plasma-spotlight/main/install.sh | bash
```

### SDDM Login Screen (Optional)
To update your login screen background, run once with sudo:
```bash
plasma-spotlight --setup-sddm-theme
```

This creates a custom theme in `/var/lib/sddm` that works on immutable filesystems. Daily updates happen without sudo via a user-writable symlink.

## Configuration

Edit `~/.config/plasma-spotlight/config.json` to customize behavior:

```json
{
  "save_path_bing": "/home/username/Pictures/Wallpapers/Bing",
  "save_path_spotlight": "/home/username/Pictures/Wallpapers/Spotlight",
  "bing_regions": ["en-US", "intl"],
  "resolution": "UHD",
  "spotlight_country": "US",
  "spotlight_locale": "en-US",
  "spotlight_batch_count": 1,
  "download_sources": "both",
  "preferred_source": "spotlight",
  "update_lockscreen": false,
  "update_sddm": false
}
```

**Note**: Replace `/home/username` with your actual home directory path, or omit the path settings to use defaults (`~/Pictures/Wallpapers/`).

**Options**:
- `bing_regions`: List of Bing market codes (e.g., `["en-US", "ja-JP", "en-GB", "intl"]`)
- `resolution`: Image quality - `"UHD"` (3840x2160), `"1920x1080"`, or `"1366x768"`
- `spotlight_batch_count`: Number of Spotlight images to fetch per run (1-4)
- `download_sources`: `"both"`, `"bing"`, or `"spotlight"`
- `preferred_source`: Which source to prefer for wallpaper selection - `"spotlight"` or `"bing"`

### Logging

Control log verbosity with the `PLASMA_SPOTLIGHT_LOG_LEVEL` environment variable:

```bash
# Default: INFO
plasma-spotlight --update-lockscreen

# Debug mode (verbose)
PLASMA_SPOTLIGHT_LOG_LEVEL=DEBUG plasma-spotlight --update-lockscreen

# Quiet mode (errors only)
PLASMA_SPOTLIGHT_LOG_LEVEL=ERROR plasma-spotlight --update-lockscreen
```

Valid levels: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

## Usage

### Manual Run
```bash
# Download and update everything
plasma-spotlight --update-lockscreen --update-sddm

# Download only (no system changes)
plasma-spotlight --download-only
```

### Automation (Recommended)
```bash
plasma-spotlight --install-timer   # Create systemd units
plasma-spotlight --enable-timer    # Start daily automation
plasma-spotlight --disable-timer   # Pause automation
plasma-spotlight --uninstall-timer # Remove automation
```

The timer runs daily and automatically updates your wallpapers. Check status with `systemctl --user status plasma-spotlight.timer`.

## How It Works

1. **Downloads**: Fetches images from Spotlight/Bing APIs to `~/Pictures/Wallpapers/`
2. **Symlinks**: Updates `~/.local/share/plasma-spotlight/current.jpg` (no sudo needed)
3. **Integrates**: Updates KDE lock screen config and SDDM theme points to symlink
4. **Metadata**: Saves image details (title, copyright, location) in `metadata/` subfolders for reference

The SDDM theme lives in `/var/lib/sddm` (one-time sudo setup), but daily updates only touch the user-writable symlink—perfect for Atomic systems.

## Uninstall

```bash
curl -fsSL https://raw.githubusercontent.com/abirkel/plasma-spotlight/main/uninstall.sh | bash
```

## Acknowledgments

Windows Spotlight API endpoint documentation from [Spotlight Downloader](https://github.com/ORelio/Spotlight-Downloader) by ORelio (CDDL-1.0).

## License

MIT
