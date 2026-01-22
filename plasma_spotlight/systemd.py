import sys
import subprocess
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

SERVICE_NAME = "plasma-spotlight.service"
TIMER_NAME = "plasma-spotlight.timer"
SYSTEMD_USER_DIR = Path.home() / ".config/systemd/user"

def get_script_path():
    """Returns the absolute path to the main run script (run.py)."""
    # Assuming this module is in src/systemd.py, and run.py is in project root
    # Or we can use sys.argv[0] if it's reliable, but safer to find relative to this file
    current_file = Path(__file__).resolve()
    project_root = current_file.parent.parent
    run_script = project_root / "run.py"
    return run_script

def generate_service_content(script_path):
    python_exec = sys.executable
    return f"""[Unit]
Description=Daily Wallpaper Downloader (Spotlight/Bing)
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart={python_exec} {script_path} --update-lockscreen --update-sddm
WorkingDirectory={script_path.parent}
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
"""

def generate_timer_content():
    return """[Unit]
Description=Daily Timer for Wallpaper Downloader

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
"""

def check_systemd_dir():
    if not SYSTEMD_USER_DIR.exists():
        try:
            SYSTEMD_USER_DIR.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.error(f"Failed to create systemd user dir: {e}")
            return False
    return True

def run_systemctl(action, unit=None, flags=None):
    """Run systemctl command with optional unit and flags.
    
    Args:
        action: systemctl action (e.g., 'enable', 'disable', 'daemon-reload')
        unit: optional unit name (e.g., 'plasma-spotlight.timer')
        flags: optional list of flags (e.g., ['--now'])
    """
    cmd = ["systemctl", "--user"]
    
    # Add flags if provided
    if flags:
        if isinstance(flags, list):
            cmd.extend(flags)
        else:
            cmd.append(flags)
    
    # Add action
    cmd.append(action)
    
    # Add unit if provided
    if unit:
        cmd.append(unit)
    
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logger.info(f"Successfully ran: {' '.join(cmd)}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to run systemctl {action}: {e.stderr.decode().strip()}")
        return False

def install_timer():
    if not check_systemd_dir():
        return False
    
    script_path = get_script_path()
    if not script_path.exists():
        logger.error(f"Could not find run.py at {script_path}")
        return False

    service_file = SYSTEMD_USER_DIR / SERVICE_NAME
    timer_file = SYSTEMD_USER_DIR / TIMER_NAME

    try:
        with open(service_file, 'w') as f:
            f.write(generate_service_content(script_path))
        logger.info(f"Created {service_file}")

        with open(timer_file, 'w') as f:
            f.write(generate_timer_content())
        logger.info(f"Created {timer_file}")
        
        # Reload daemon to pick up new files
        run_systemctl("daemon-reload")
        return True
    except OSError as e:
        logger.error(f"Failed to write unit files: {e}")
        return False

def uninstall_timer():
    # Stop/Disable first
    disable_timer()
    
    service_file = SYSTEMD_USER_DIR / SERVICE_NAME
    timer_file = SYSTEMD_USER_DIR / TIMER_NAME
    
    try:
        if timer_file.exists():
            timer_file.unlink()
            logger.info(f"Removed {timer_file}")
        
        if service_file.exists():
            service_file.unlink()
            logger.info(f"Removed {service_file}")
            
        run_systemctl("daemon-reload")
        return True
    except OSError as e:
        logger.error(f"Failed to remove unit files: {e}")
        return False

def enable_timer():
    # We only enable the timer, not the service (since it's oneshot triggered by timer)
    return run_systemctl("enable", TIMER_NAME, flags=["--now"])

def disable_timer():
    return run_systemctl("disable", TIMER_NAME, flags=["--now"])
