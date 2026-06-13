#!/bin/sh
# Build macOS .dmg for Telepresence Manager
#
# Usage:
#   ./installer/build-macos.sh <version>

set -e

VERSION="${1:?Usage: $0 <version>}"
DIST_DIR="dist"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
DMG_NAME="TelepresenceManager-${VERSION}.dmg"
APP_NAME="Telepresence Manager.app"

cd "$PROJECT_DIR"

echo "==> Creating .app bundle structure..."

# Clean any previous bundle
rm -rf "dist/$APP_NAME"
mkdir -p "dist/$APP_NAME/Contents/MacOS"
mkdir -p "dist/$APP_NAME/Contents/Resources"

# Copy the binary
cp "dist/TelepresenceManager" "dist/$APP_NAME/Contents/MacOS/TelepresenceManager"
chmod 755 "dist/$APP_NAME/Contents/MacOS/TelepresenceManager"

# Create Info.plist
cat > "dist/$APP_NAME/Contents/Info.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>TelepresenceManager</string>
    <key>CFBundleIdentifier</key>
    <string>io.github.hueidou.telepresence-manager</string>
    <key>CFBundleName</key>
    <string>Telepresence Manager</string>
    <key>CFBundleVersion</key>
    <string>${VERSION}</string>
    <key>CFBundleShortVersionString</key>
    <string>${VERSION}</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>LSMinimumSystemVersion</key>
    <string>12.0</string>
    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>
EOF

echo "==> Creating .dmg..."

# Remove previous DMG
rm -f "dist/$DMG_NAME"

# Create temporary DMG
hdiutil create -volname "Telepresence Manager" \
    -srcfolder "dist/$APP_NAME" \
    -ov -format UDZO \
    "dist/$DMG_NAME"

# Clean up temporary .app bundle
rm -rf "dist/$APP_NAME"

echo "  => Created: dist/$DMG_NAME"
echo "==> macOS packaging complete!"
