#!/bin/sh
# Build UDM.app with PyInstaller and wrap it in a drag-to-install DMG.
#
# Usage: conda run -n mine packaging/macos/build_dmg.sh
# Output: dist/UDM-<version>-macos-<arch>.dmg
set -eu

ROOT=$(cd "$(dirname "$0")/../.." && pwd)
PYTHON=${PYTHON:-python}
VERSION=$(tr -d '[:space:]' < "$ROOT/VERSION")
BUILD="$ROOT/build/macos"
DIST="$ROOT/dist"
STAGING="$BUILD/dmg"
DMG="$DIST/UDM-$VERSION-macos-$(uname -m).dmg"

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

echo "Compiling the Safari extension"
# Users without developer tools get these prebuilt binaries; see
# udm/bridge/safari.py.
SAFARI_BIN="$BUILD/safari-bin"
PYTHONPATH="$ROOT" "$PYTHON" -c \
    "import sys; from udm.bridge.safari import compile_binaries; compile_binaries(sys.argv[1])" \
    "$SAFARI_BIN"

echo "Building UDM.app $VERSION"
UDM_ICON="$BUILD/UDM.icns" UDM_SAFARI_BIN="$SAFARI_BIN" "$PYTHON" -m PyInstaller \
    --noconfirm --clean \
    --distpath "$BUILD/dist" \
    --workpath "$BUILD/work" \
    "$ROOT/packaging/udm.spec"

APP="$BUILD/dist/UDM.app"
# PyInstaller signs ad hoc; re-sign the whole bundle so Apple silicon accepts
# the bundled FFmpeg and Qt plugins after any post-build changes.
codesign --force --deep --sign - "$APP"

echo "Packaging $DMG"
mkdir -p "$STAGING"
cp -R "$APP" "$STAGING/"
ln -s /Applications "$STAGING/Applications"
rm -f "$DMG"
# hdiutil fails intermittently with "Resource busy" while macOS scans the
# fresh bundle (common on CI runners), so retry a few times.
attempt=1
until hdiutil create -volname "UDM $VERSION" -srcfolder "$STAGING" -ov -format UDZO "$DMG" >/dev/null; do
    if [ "$attempt" -ge 5 ]; then
        echo "hdiutil failed after $attempt attempts" >&2
        exit 1
    fi
    attempt=$((attempt + 1))
    echo "hdiutil failed; retrying (attempt $attempt)"
    sleep 10
done

echo "Done: $DMG"
