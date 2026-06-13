"""Telepresence Manager — Entry Point."""

import os
import sys
import ctypes
import time
import webview
from app.logger import info, debug, error as log_error

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.api import Api


def _set_title_bar_color(title, r, g, b):
    """Set the Windows title bar color to match the app theme."""
    if os.name != "nt":
        return
    try:
        hwnd = ctypes.windll.user32.FindWindowW(None, title)
        if not hwnd:
            return
        # DWMWA_USE_IMMERSIVE_DARK_MODE = 20 (enable dark mode first)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, 20, ctypes.byref(ctypes.c_int(1)), ctypes.sizeof(ctypes.c_int)
        )
        # DWMWA_CAPTION_COLOR = 35 (set custom caption color, COLORREF: 0x00BBGGRR)
        color_ref = r | (g << 8) | (b << 16)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, 35, ctypes.byref(ctypes.c_int(color_ref)), ctypes.sizeof(ctypes.c_int)
        )
    except Exception:
        pass


def _read_version():
    """Read version from VERSION file."""
    # When frozen by PyInstaller, look next to the exe; otherwise in project root
    if getattr(sys, 'frozen', False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    version_file = os.path.join(base, 'VERSION')
    # PyInstaller onefile extracts data to sys._MEIPASS
    if not os.path.isfile(version_file) and hasattr(sys, '_MEIPASS'):
        version_file = os.path.join(sys._MEIPASS, 'VERSION')
    try:
        with open(version_file, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except FileNotFoundError:
        return 'dev'


def _resolve_web_path():
    """Resolve the web directory path, supporting both dev and frozen modes."""
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, 'web', 'index.html')
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, 'web', 'index.html')


def main():
    info("Starting Telepresence Manager")
    debug("Python %s, platform=%s, frozen=%s", sys.version, sys.platform, getattr(sys, 'frozen', False))

    api = Api()

    version = _read_version()
    api.set_version(version)
    html_path = _resolve_web_path()
    window_title = f"Telepresence Manager v{version}"

    info("Version=%s, web=%s", version, html_path)

    window = webview.create_window(
        title=window_title,
        url=html_path,
        js_api=api,
        width=900,
        height=640,
        min_size=(700, 500),
        resizable=True,
        text_select=True,
    )

    def on_loaded():
        # Small delay to ensure window is fully created
        time.sleep(0.3)
        info("Window loaded, setting title bar color")
        # Match --bg color #1a1b2e (R=0x1a, G=0x1b, B=0x2e)
        _set_title_bar_color(window_title, 0x1a, 0x1b, 0x2e)

    webview.start(on_loaded, debug=False)
    info("Application exited")


if __name__ == "__main__":
    main()
