"""Telepresence Manager — Entry Point."""

import os
import sys
import webview

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.api import Api


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
    api = Api()

    version = _read_version()
    html_path = _resolve_web_path()

    window = webview.create_window(
        title=f"Telepresence Manager v{version}",
        url=html_path,
        js_api=api,
        width=900,
        height=640,
        min_size=(700, 500),
        resizable=True,
        text_select=True,
    )

    webview.start(debug=False)


if __name__ == "__main__":
    main()
