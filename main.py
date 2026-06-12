"""Telepresence Manager — Entry Point."""

import os
import sys
import webview

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.api import Api


def main():
    api = Api()

    # Resolve web directory path
    base_dir = os.path.dirname(os.path.abspath(__file__))
    html_path = os.path.join(base_dir, "web", "index.html")

    window = webview.create_window(
        title="Telepresence Manager",
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
