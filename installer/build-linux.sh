#!/bin/sh
# Build Linux installer artifacts for Telepresence Manager
#
# Prerequisites (Ubuntu/Debian):
#   sudo apt install libwebkit2gtk-4.1-dev
#
# Usage:
#   ./installer/build-linux.sh <version>

set -e

VERSION="${1:?Usage: $0 <version>}"
DIST_DIR="dist"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_DIR"

echo "==> Packaging Linux release: TelepresenceManager-${VERSION}-linux.tar.gz"
# Already built by scripts/build.py into dist/

echo "==> Creating .deb package (optional)..."
if command -v dpkg-deb >/dev/null 2>&1; then
    DEB_DIR="deb-build/telepresence-manager_${VERSION}_amd64"
    mkdir -p "$DEB_DIR/DEBIAN"
    mkdir -p "$DEB_DIR/usr/local/bin"
    mkdir -p "$DEB_DIR/usr/share/applications"
    mkdir -p "$DEB_DIR/usr/share/icons/hicolor/256x256/apps"

    # Control file
    cat > "$DEB_DIR/DEBIAN/control" <<EOF
Package: telepresence-manager
Version: $VERSION
Section: admin
Priority: optional
Architecture: amd64
Maintainer: hueidou
Description: Desktop GUI for managing Telepresence connections
 Built with Python + pywebview (WebKit2GTK).
Depends: libwebkit2gtk-4.1-0
EOF

    # Desktop entry
    cat > "$DEB_DIR/usr/share/applications/telepresence-manager.desktop" <<EOF
[Desktop Entry]
Name=Telepresence Manager
Comment=Manage Telepresence connections
Exec=/usr/local/bin/TelepresenceManager
Icon=telepresence-manager
Terminal=false
Type=Application
Categories=Network;Utility;
EOF

    # Binary
    cp "$DIST_DIR/TelepresenceManager" "$DEB_DIR/usr/local/bin/"
    chmod 755 "$DEB_DIR/usr/local/bin/TelepresenceManager"

    dpkg-deb --build "$DEB_DIR" "$DIST_DIR/TelepresenceManager-${VERSION}.deb"
    rm -rf deb-build
    echo "  => Created: dist/TelepresenceManager-${VERSION}.deb"
else
    echo "  => dpkg-deb not found, skipping .deb package"
fi

echo "==> Linux packaging complete!"
