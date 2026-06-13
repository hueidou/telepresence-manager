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
BUNDLE_PATH="dist/$APP_NAME"

cd "$PROJECT_DIR"

echo "==> Creating .app bundle structure..."

# Clean any previous bundle
rm -rf "$BUNDLE_PATH"
mkdir -p "$BUNDLE_PATH/Contents/MacOS"
mkdir -p "$BUNDLE_PATH/Contents/Resources"

# Copy the binary
cp "dist/TelepresenceManager" "$BUNDLE_PATH/Contents/MacOS/TelepresenceManager"
chmod 755 "$BUNDLE_PATH/Contents/MacOS/TelepresenceManager"

# Create Info.plist
cat > "$BUNDLE_PATH/Contents/Info.plist" <<EOF
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
    <key>NSAppTransportSecurity</key>
    <dict>
        <key>NSAllowsArbitraryLoads</key>
        <true/>
    </dict>
</dict>
</plist>
EOF

# Ad-hoc code sign the .app bundle
echo "==> Ad-hoc code signing..."
codesign --force --deep --sign - "$BUNDLE_PATH" 2>&1 || echo "  (code signing skipped — not a macOS CI runner?)"

echo "==> Creating .dmg..."

# Remove previous DMG
rm -f "dist/$DMG_NAME"

# Create a temporary directory for DMG contents
DMG_TMP="dist/dmg-tmp"
rm -rf "$DMG_TMP"
mkdir -p "$DMG_TMP"

# Copy .app into DMG staging
cp -R "$BUNDLE_PATH" "$DMG_TMP/"

# Add a symbolic link to /Applications for easy install
ln -s /Applications "$DMG_TMP/Applications"

# Add README with first-run instructions
cat > "$DMG_TMP/README.txt" <<EOF
Telepresence Manager v${VERSION}

== First run on macOS ==

The first time you open this app, macOS Gatekeeper will show:
  "TelepresenceManager is damaged and can't be opened"

This is NOT because the app is damaged — it's because the app is
not signed with an Apple Developer certificate (an expensive
annual subscription required by Apple).

To fix, run this command in Terminal after dragging the app to
Applications:

    sudo xattr -dr com.apple.quarantine /Applications/Telepresence\\ Manager.app

Then right-click the app in Finder and select "Open" to launch it.
You only need to do this once.

== Prerequisites ==

- telepresence v2.x (https://www.telepresence.io/)
- kubectl (https://kubernetes.io/docs/tasks/tools/)
- macOS 12+
EOF

# Create the DMG
hdiutil create -volname "Telepresence Manager" \
    -srcfolder "$DMG_TMP" \
    -ov -format UDZO \
    "dist/$DMG_NAME"

# Clean up
rm -rf "$DMG_TMP" "$BUNDLE_PATH"

echo "  => Created: dist/$DMG_NAME"
echo "==> macOS packaging complete!"
