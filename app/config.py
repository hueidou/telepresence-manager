"""Application configuration management.

Config stored at ~/.kube/telepresence-manager.json
"""

import os
import json
import locale
from app.logger import debug, info, error as log_error

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".kube")
CONFIG_FILE = os.path.join(CONFIG_DIR, "telepresence-manager.json")

DEFAULT_CONFIG = {
    "language": "auto",
    "refreshInterval": 30,
}


def load():
    """Load config from ~/.kube/telepresence-manager.json.

    Merges with defaults so missing keys are filled in.
    Returns dict.
    """
    try:
        if os.path.isfile(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            if isinstance(cfg, dict):
                merged = DEFAULT_CONFIG.copy()
                merged.update(cfg)
                debug("Config loaded from %s: %s", CONFIG_FILE, merged)
                return merged
    except (json.JSONDecodeError, OSError) as e:
        log_error("Failed to load config: %s", e)
    debug("Using default config")
    return DEFAULT_CONFIG.copy()


def save(config):
    """Save config to ~/.kube/telepresence-manager.json.

    Args:
        config: dict of config values to save.

    Returns:
        bool: True on success.
    """
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        merged = DEFAULT_CONFIG.copy()
        merged.update(config)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(merged, f, indent=2, ensure_ascii=False)
        info("Config saved to %s: %s", CONFIG_FILE, merged)
        return True
    except OSError as e:
        log_error("Failed to save config: %s", e)
        return False


def get_system_language():
    """Detect the system UI language.

    Returns:
        str: "zh" for Chinese, "en" for English.
    """
    try:
        # getlocale() returns (lang_code, encoding) — e.g. ("zh_CN", "UTF-8")
        lang_code, _ = locale.getlocale(locale.LC_CTYPE)
        if lang_code:
            lang_code = lang_code.split("_")[0]  # "zh_CN" -> "zh"
            if lang_code == "zh":
                return "zh"
    except Exception:
        pass
    return "en"
