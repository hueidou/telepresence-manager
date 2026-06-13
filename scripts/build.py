#!/usr/bin/env python3
"""Build script for Telepresence Manager.

Cross-platform: Windows, macOS, Linux.

Generates:
  Windows:
    - dist/TelepresenceManager.exe
    - dist/TelepresenceManager-{version}-win.zip
  macOS:
    - dist/TelepresenceManager
    - dist/TelepresenceManager-{version}-macos.tar.gz
    - dist/TelepresenceManager-{version}.dmg (via installer/build-macos.sh)
  Linux:
    - dist/TelepresenceManager
    - dist/TelepresenceManager-{version}-linux.tar.gz

Usage:
    python scripts/build.py [--clean]
"""

import argparse
import io
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import zipfile

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST_DIR = os.path.join(BASE_DIR, 'dist')
SPEC_FILE = os.path.join(BASE_DIR, 'telepresence_manager.spec')
VERSION_FILE = os.path.join(BASE_DIR, 'VERSION')

# ── Platform detection ──
SYSTEM = platform.system()  # 'Windows', 'Darwin', 'Linux'
IS_WINDOWS = SYSTEM == 'Windows'
IS_MACOS = SYSTEM == 'Darwin'
IS_LINUX = SYSTEM == 'Linux'

EXE_NAME = 'TelepresenceManager.exe' if IS_WINDOWS else 'TelepresenceManager'
ARCHIVE_SUFFIX = 'win.zip' if IS_WINDOWS else ('macos.tar.gz' if IS_MACOS else 'linux.tar.gz')


def read_version():
    """Read version string from VERSION file."""
    with open(VERSION_FILE, 'r', encoding='utf-8') as f:
        return f.read().strip()


def clean():
    """Remove previous build artifacts."""
    for d in ['build', 'dist']:
        path = os.path.join(BASE_DIR, d)
        if os.path.isdir(path):
            print(f'Removing {path}')
            shutil.rmtree(path)


def run_pyinstaller():
    """Run PyInstaller with the project spec file."""
    print('Building executable with PyInstaller...')
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--clean',
        '--noconfirm',
        SPEC_FILE,
    ]
    result = subprocess.run(cmd, cwd=BASE_DIR)
    if result.returncode != 0:
        print('PyInstaller build failed!', file=sys.stderr)
        sys.exit(1)

    exe_path = os.path.join(DIST_DIR, EXE_NAME)
    if not os.path.isfile(exe_path):
        print(f'Expected exe not found: {exe_path}', file=sys.stderr)
        sys.exit(1)

    size_mb = os.path.getsize(exe_path) / (1024 * 1024)
    print(f'Built: {exe_path} ({size_mb:.1f} MB)')
    return exe_path


def create_portable_archive(version):
    """Create a portable archive (zip on Windows, tar.gz on Linux/macOS)."""
    archive_name = f'TelepresenceManager-{version}-{ARCHIVE_SUFFIX}'
    archive_path = os.path.join(DIST_DIR, archive_name)
    exe_path = os.path.join(DIST_DIR, EXE_NAME)

    # Platform-specific README
    if IS_WINDOWS:
        readme_text = (
            '# Telepresence Manager\n\n'
            'Double-click TelepresenceManager.exe to launch.\n\n'
            'Prerequisites:\n'
            '- Windows 10/11\n'
            '- telepresence v2.x (https://www.telepresence.io/)\n'
            '- kubectl (https://kubernetes.io/docs/tasks/tools/)\n'
            '- Edge WebView2 Runtime (built-in on Windows 10/11)\n'
        )
    elif IS_MACOS:
        readme_text = (
            '# Telepresence Manager\n\n'
            'Run ./TelepresenceManager to launch.\n\n'
            'Prerequisites:\n'
            '- macOS 12+\n'
            '- telepresence v2.x (https://www.telepresence.io/)\n'
            '- kubectl (https://kubernetes.io/docs/tasks/tools/)\n'
            '- WebKit (built-in on macOS)\n'
            '- PyWebView requires PyObjC (installed automatically)\n'
        )
    else:
        readme_text = (
            '# Telepresence Manager\n\n'
            'Run ./TelepresenceManager to launch.\n\n'
            'Prerequisites:\n'
            '- Linux with X11/Wayland\n'
            '- telepresence v2.x (https://www.telepresence.io/)\n'
            '- kubectl (https://kubernetes.io/docs/tasks/tools/)\n'
            '- WebKit2GTK (sudo apt install libwebkit2gtk-4.1-dev)\n'
        )

    print(f'Creating portable package: {archive_name}')

    if IS_WINDOWS:
        with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.write(exe_path, EXE_NAME)
            zf.writestr('README.txt', readme_text)
    else:
        with tarfile.open(archive_path, 'w:gz') as tf:
            tf.add(exe_path, arcname=EXE_NAME)
            # Add README as a TarInfo with content
            readme_info = tarfile.TarInfo(name='README.txt')
            readme_bytes = readme_text.encode('utf-8')
            readme_info.size = len(readme_bytes)
            tf.addfile(readme_info, io.BytesIO(readme_bytes))

    size_mb = os.path.getsize(archive_path) / (1024 * 1024)
    print(f'Created: {archive_path} ({size_mb:.1f} MB)')
    return archive_path


def main():
    parser = argparse.ArgumentParser(description='Build Telepresence Manager')
    parser.add_argument('--clean', action='store_true', help='Clean build artifacts before building')
    args = parser.parse_args()

    version = read_version()
    print(f'Version: {version}')
    print(f'Platform: {SYSTEM}')
    print(f'Executable: {EXE_NAME}')

    if args.clean:
        clean()

    os.makedirs(DIST_DIR, exist_ok=True)
    run_pyinstaller()
    create_portable_archive(version)
    print('\nBuild complete!')


if __name__ == '__main__':
    main()
