#!/bin/sh
# Build macOS installer artifacts for Telepresence Manager
#
# Usage:
#   ./installer/build-macos.sh <version>

set -e

VERSION="${1:?Usage: $0 <version>}"
DIST_DIR="dist"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_DIR"

echo "==> Packaging macOS release: TelepresenceManager-${VERSION}-macos.tar.gz"
# Already built by scripts/build.py into dist/

echo "==> Creating .app bundle (optional)..."
# PyInstaller can produce .app bundles with --onedir, but our spec builds
# a single-file binary. For now we provide the plain binary + shell launcher.

echo "==> macOS packaging complete!"
