"""Capture screenshots of the Telepresence Manager app."""

import subprocess
import time
import sys
import os

# Launch app in background
proc = subprocess.Popen(
    [sys.executable, "main.py"],
    cwd=os.path.dirname(os.path.abspath(__file__)),
)

# Wait for window to appear and render
print("Waiting for app to start...")
time.sleep(5)

# Take screenshot
from PIL import ImageGrab

screenshot = ImageGrab.grab()
screenshot.save("assets/screenshot_full.png")
print("Full screenshot saved to assets/screenshot_full.png")

# Try to find and crop the app window
# The window should be around 900x640
# Let's also save the full screenshot for reference
width, height = screenshot.size
print(f"Screen size: {width}x{height}")

# Terminate app
proc.terminate()
proc.wait(timeout=5)
print("App terminated.")
