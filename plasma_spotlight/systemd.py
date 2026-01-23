"""Systemd timer management for plasma-spotlight.

This module contains ONLY runtime functions for enabling/disabling the timer.
Installation of the timer is handled by install.sh.
"""

import subprocess
import logging

logger = logging.getLogger(__name__)

TIMER_NAME = "plasma-spotlight.timer"


def enable_timer() -> bool:
    """Enable and start the systemd user timer.

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        subprocess.run(
            ["systemctl", "--user", "enable", "--now", TIMER_NAME],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        logger.info(f"Enabled and started {TIMER_NAME}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to enable timer: {e.stderr.decode().strip()}")
        return False


def disable_timer() -> bool:
    """Disable and stop the systemd user timer.

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        subprocess.run(
            ["systemctl", "--user", "disable", "--now", TIMER_NAME],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        logger.info(f"Disabled and stopped {TIMER_NAME}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to disable timer: {e.stderr.decode().strip()}")
        return False
