"""Version check and auto-update via GitHub Releases.

Supports Windows, macOS, and Linux.
"""

import os
import sys
import json
import tempfile
import subprocess
import urllib.request
import urllib.error

GITHUB_REPO = "hueidou/telepresence-manager"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


def _parse_version(v):
    """Parse version string like '1.2.3' into comparable tuple."""
    try:
        parts = v.strip().lstrip("v").split(".")
        return tuple(int(p) for p in parts)
    except (ValueError, AttributeError):
        return (0, 0, 0)


def _get_exe_path():
    """Get the path of the current executable."""
    if getattr(sys, 'frozen', False):
        return sys.executable
    return None


def _platform_asset_suffix():
    """Return the platform-appropriate asset name suffix to look for in releases.

    Returns:
        str: e.g. 'win.zip', 'macos.tar.gz', 'linux.tar.gz'
    """
    if os.name == "nt":
        return "win.zip"
    elif sys.platform == "darwin":
        return "macos.tar.gz"
    else:
        return "linux.tar.gz"


def _platform_exe_name():
    """Return the platform-appropriate executable filename for download."""
    if os.name == "nt":
        return "TelepresenceManager.exe"
    else:
        return "TelepresenceManager"


def check_for_update(current_version):
    """Check GitHub Releases for a newer version.

    Returns dict:
      {available: bool, current_version: str, latest_version: str,
       download_url: str, body: str, error: str|None}
    """
    result = {
        "available": False,
        "current_version": current_version,
        "latest_version": current_version,
        "download_url": "",
        "body": "",
        "error": None,
    }

    suffix = _platform_asset_suffix()

    try:
        req = urllib.request.Request(
            GITHUB_API_URL,
            headers={"Accept": "application/vnd.github.v3+json", "User-Agent": "TelepresenceManager"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        latest_tag = data.get("tag_name", "")
        latest_version = latest_tag.lstrip("v")
        result["latest_version"] = latest_version

        if _parse_version(latest_version) > _parse_version(current_version):
            result["available"] = True
            result["body"] = data.get("body", "")

            # Find the platform-appropriate asset
            for asset in data.get("assets", []):
                name = asset.get("name", "")
                if name.endswith(suffix) or name == _platform_exe_name():
                    result["download_url"] = asset.get("browser_download_url", "")
                    break

    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, KeyError) as e:
        result["error"] = str(e)
    except Exception as e:
        result["error"] = str(e)

    return result


def download_update(url, progress_callback=None):
    """Download the new executable to a temp directory.

    Args:
        url: Download URL for the new executable
        progress_callback: Optional callable(percent: int) for progress updates

    Returns:
        str: Path to downloaded file, or empty string on failure
    """
    if not url:
        return ""

    dest_dir = tempfile.mkdtemp(prefix="tp_update_")
    exe_name = _platform_exe_name()
    dest_path = os.path.join(dest_dir, exe_name)

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "TelepresenceManager"})
        with urllib.request.urlopen(req, timeout=300) as resp:
            total = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            chunk_size = 65536

            with open(dest_path, "wb") as f:
                while True:
                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback and total > 0:
                        progress_callback(int(downloaded * 100 / total))

        if progress_callback:
            progress_callback(100)

        # Make executable on Linux/macOS
        if os.name != "nt":
            os.chmod(dest_path, 0o755)

        return dest_path

    except Exception:
        # Clean up on failure
        try:
            os.remove(dest_path)
            os.rmdir(dest_dir)
        except OSError:
            pass
        return ""


def apply_update(downloaded_path):
    """Apply the update by creating a platform-appropriate script to replace the exe and restart.

    The script will:
    1. Wait for the current process to exit
    2. Replace the old exe with the new one
    3. Launch the new exe
    4. Delete itself

    Returns:
        bool: True if the update script was launched successfully
    """
    exe_path = _get_exe_path()
    if not exe_path or not downloaded_path or not os.path.isfile(downloaded_path):
        return False

    try:
        exe_dir = os.path.dirname(exe_path)
        downloaded_dir = os.path.dirname(downloaded_path)

        if os.name == "nt":
            return _apply_update_windows(exe_path, exe_dir, downloaded_path, downloaded_dir)
        else:
            return _apply_update_posix(exe_path, exe_dir, downloaded_path, downloaded_dir)

    except Exception:
        return False


def _apply_update_windows(exe_path, exe_dir, downloaded_path, downloaded_dir):
    """Apply update on Windows using a batch script."""
    bat_path = os.path.join(exe_dir, "_update.bat")

    bat_content = f"""@echo off
chcp 65001 >nul 2>&1
echo Waiting for application to close...
timeout /t 2 /nobreak >nul
echo Replacing application...
copy /y "{downloaded_path}" "{exe_path}" >nul
if errorlevel 1 (
    echo Update failed. Please replace manually.
    pause
    goto cleanup
)
echo Starting new version...
start "" "{exe_path}"
:cleanup
del "{downloaded_path}" >nul 2>&1
rd "{downloaded_dir}" >nul 2>&1
del "%~f0"
"""
    with open(bat_path, "w", encoding="utf-8") as f:
        f.write(bat_content)

    subprocess.Popen(
        ["cmd.exe", "/c", bat_path],
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        cwd=exe_dir,
    )
    return True


def _apply_update_posix(exe_path, exe_dir, downloaded_path, downloaded_dir):
    """Apply update on Linux/macOS using a shell script."""
    sh_path = os.path.join(exe_dir, "_update.sh")

    sh_content = f"""#!/bin/sh
echo 'Waiting for application to close...'
sleep 2
echo 'Replacing application...'
cp -f "{downloaded_path}" "{exe_path}"
if [ $? -ne 0 ]; then
    echo 'Update failed. Please replace manually.'
    exit 1
fi
echo 'Starting new version...'
nohup "{exe_path}" >/dev/null 2>&1 &
rm -f "{downloaded_path}"
rm -rf "{downloaded_dir}"
rm -f "$0"
"""
    with open(sh_path, "w", encoding="utf-8") as f:
        f.write(sh_content)

    os.chmod(sh_path, 0o755)

    subprocess.Popen(
        ["/bin/sh", sh_path],
        cwd=exe_dir,
    )
    return True
