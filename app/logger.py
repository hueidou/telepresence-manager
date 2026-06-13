"""Application logging.

Writes structured logs to ~/.kube/telepresence-manager.log
with automatic size management (max 5 MB, 3 backup files).
"""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler

LOG_DIR = os.path.join(os.path.expanduser("~"), ".kube")
LOG_FILE = os.path.join(LOG_DIR, "telepresence-manager.log")
LOG_MAX_BYTES = 5 * 1024 * 1024  # 5 MB
LOG_BACKUP_COUNT = 3

_logger = None


def _get_logger():
    """Get or create the application logger (singleton)."""
    global _logger
    if _logger is not None:
        return _logger

    _logger = logging.getLogger("TelepresenceManager")
    _logger.setLevel(logging.DEBUG)

    # Prevent duplicate handlers on repeated calls
    if _logger.handlers:
        return _logger

    # Ensure log directory exists
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
    except OSError:
        pass

    # File handler with rotation
    try:
        fh = RotatingFileHandler(
            LOG_FILE, maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUP_COUNT,
            encoding="utf-8",
        )
        fh.setLevel(logging.DEBUG)
    except (OSError, IOError):
        # Fall back to stderr if log file can't be created
        fh = logging.StreamHandler(sys.stderr)
        fh.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        fmt="%(asctime)s  %(levelname)-8s  %(name)s.%(funcName)s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    fh.setFormatter(formatter)
    _logger.addHandler(fh)

    return _logger


def debug(msg, *args, **kwargs):
    _get_logger().debug(msg, *args, **kwargs)


def info(msg, *args, **kwargs):
    _get_logger().info(msg, *args, **kwargs)


def warning(msg, *args, **kwargs):
    _get_logger().warning(msg, *args, **kwargs)


def error(msg, *args, **kwargs):
    _get_logger().error(msg, *args, **kwargs)


def exception(msg, *args, **kwargs):
    _get_logger().exception(msg, *args, **kwargs)
