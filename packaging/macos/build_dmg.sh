#!/bin/sh
# Build UDM.app with PyInstaller and wrap it in a drag-to-install DMG.
#
# Usage: conda run -n mine packaging/macos/build_dmg.sh
# Output: dist/UDM-<version>.dmg
set -eu

ROOT=$(cd "$(dirname "$0")/../.." && pwd)
PYTHON=${PYTHON:-python}
VERSION=$(tr -d '[:space:]' < "$ROOT/VERSION")
BUILD="$ROOT/build/macos"
DIST="$ROOT/dist"
STAGING="$BUILD/dmg"
DMG="$DIST/UDM-$VERSION.dmg"

rm -rf "$BUILD"
mkdir -p "$BUILD" "$DIST"

echo "Creating application icon"
ICONSET="$BUILD/UDM.iconset"
mkdir -p "$ICONSET"
for size in 16 32 128 256 512; do
    sips -z "$size" "$size" "$ROOT/logo.png" --out "$ICONSET/icon_${size}x${size}.png" >/dev/null
    double=$((size * 2))
    sips -z "$double" "$double" "$ROOT/logo.png" --out "$ICONSET/icon_${size}x${size}@2x.png" >/dev/null
done
iconutil -c icns "$ICONSET" -o "$BUILD/UDM.icns"

echo "Building UDM.app $VERSION"
UDM_ICNS="$BUILD/UDM.icns" "$PYTHON" -m PyInstaller \
    --noconfirm --clean \
    --distpath "$BUILD/dist" \
    --workpath "$BUILD/work" \
    "$ROOT/packaging/macos/udm.spec"

APP="$BUILD/dist/UDM.app"
# PyInstaller signs ad hoc; re-sign the whole bundle so Apple silicon accepts
# the bundled FFmpeg and Qt plugins after any post-build changes.
codesign --force --deep --sign - "$APP"

echo "Packaging $DMG"
mkdir -p "$STAGING"
cp -R "$APP" "$STAGING/"
ln -s /Applications "$STAGING/Applications"
rm -f "$DMG"
hdiutil create -volname "UDM $VERSION" -srcfolder "$STAGING" -ov -format UDZO "$DMG" >/dev/null

echo "Done: $DMG"
