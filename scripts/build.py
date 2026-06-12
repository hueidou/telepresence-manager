#!/usr/bin/env python3
"""Build script for Telepresence Manager.

Generates:
  - dist/TelepresenceManager.exe       (single-file executable)
  - dist/TelepresenceManager-*-portable.zip  (portable package)

Usage:
    python scripts/build.py [--clean]
"""

import argparse
import os
import shutil
import subprocess
import sys
import zipfile

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST_DIR = os.path.join(BASE_DIR, 'dist')
SPEC_FILE = os.path.join(BASE_DIR, 'telepresence_manager.spec')
VERSION_FILE = os.path.join(BASE_DIR, 'VERSION')


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

    exe_path = os.path.join(DIST_DIR, 'TelepresenceManager.exe')
    if not os.path.isfile(exe_path):
        print(f'Expected exe not found: {exe_path}', file=sys.stderr)
        sys.exit(1)

    size_mb = os.path.getsize(exe_path) / (1024 * 1024)
    print(f'Built: {exe_path} ({size_mb:.1f} MB)')
    return exe_path


def create_portable_zip(version):
    """Create a portable ZIP package containing the exe and a README."""
    zip_name = f'TelepresenceManager-{version}-portable.zip'
    zip_path = os.path.join(DIST_DIR, zip_name)
    exe_path = os.path.join(DIST_DIR, 'TelepresenceManager.exe')

    print(f'Creating portable package: {zip_name}')
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.write(exe_path, 'TelepresenceManager.exe')
        # Add a brief usage note
        readme_content = (
            '# Telepresence Manager\n\n'
            'Double-click TelepresenceManager.exe to launch.\n\n'
            'Prerequisites:\n'
            '- Windows 10/11\n'
            '- telepresence v2.x (https://www.telepresence.io/)\n'
            '- kubectl (https://kubernetes.io/docs/tasks/tools/)\n'
            '- Edge WebView2 Runtime (built-in on Windows 10/11)\n'
        )
        zf.writestr('README.txt', readme_content)

    size_mb = os.path.getsize(zip_path) / (1024 * 1024)
    print(f'Created: {zip_path} ({size_mb:.1f} MB)')
    return zip_path


def main():
    parser = argparse.ArgumentParser(description='Build Telepresence Manager')
    parser.add_argument('--clean', action='store_true', help='Clean build artifacts before building')
    args = parser.parse_args()

    version = read_version()
    print(f'Version: {version}')

    if args.clean:
        clean()

    os.makedirs(DIST_DIR, exist_ok=True)
    run_pyinstaller()
    create_portable_zip(version)
    print('\nBuild complete!')


if __name__ == '__main__':
    main()
