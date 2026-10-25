#!/bin/sh
# Build UDM with PyInstaller and package it as .deb, .rpm, Arch, and tarball.
#
# Usage: packaging/linux/build_packages.sh
# Requires: fpm, rpmbuild (for .rpm), and bsdtar (for the Arch package).
# Output: dist/udm_<version>_amd64.deb, dist/udm-<version>-1.x86_64.rpm,
#         dist/udm-<version>-1-x86_64.pkg.tar.xz, dist/UDM-<version>-linux-x86_64.tar.gz
set -eu

ROOT=$(cd "$(dirname "$0")/../.." && pwd)
PYTHON=${PYTHON:-python}
VERSION=$(tr -d '[:space:]' < "$ROOT/VERSION")
BUILD="$ROOT/build/linux"
DIST="$ROOT/dist"
STAGING="$BUILD/root"

rm -rf "$BUILD"
mkdir -p "$BUILD" "$DIST"

echo "Building UDM $VERSION"
"$PYTHON" -m PyInstaller \
    --noconfirm --clean \
    --distpath "$BUILD/dist" \
    --workpath "$BUILD/work" \
    "$ROOT/packaging/udm.spec"

echo "Staging the install tree"
mkdir -p "$STAGING/opt" "$STAGING/usr/bin" \
    "$STAGING/usr/share/applications" "$STAGING/usr/share/pixmaps"
cp -R "$BUILD/dist/UDM" "$STAGING/opt/udm"
ln -s /opt/udm/UDM "$STAGING/usr/bin/udm"
cp "$ROOT/packaging/linux/udm.desktop" "$STAGING/usr/share/applications/udm.desktop"
cp "$ROOT/logo.png" "$STAGING/usr/share/pixmaps/udm.png"

tar -C "$BUILD/dist" -czf "$DIST/UDM-$VERSION-linux-x86_64.tar.gz" UDM

# Qt's xcb platform plugin needs these system libraries; everything else is
# bundled by PyInstaller.
package() {
    fpm --force --input-type dir --chdir "$STAGING" \
        --name udm --version "$VERSION" --iteration 1 \
        --architecture x86_64 \
        --description "Umbrella Download Manager" \
        --url "https://github.com/NimaDolatabadi/UDM" \
        --maintainer "Nima Dolatabadi" \
        "$@" opt usr
}

echo "Packaging .deb"
package --output-type deb --package "$DIST/udm_${VERSION}_amd64.deb" \
    --depends libxcb-cursor0 --depends libxkbcommon-x11-0 \
    --depends libegl1 --depends libfontconfig1 --depends libdbus-1-3

echo "Packaging .rpm"
package --output-type rpm --package "$DIST/udm-$VERSION-1.x86_64.rpm" \
    --rpm-os linux \
    --depends xcb-util-cursor --depends libxkbcommon-x11 \
    --depends libglvnd-egl --depends fontconfig --depends dbus-libs

echo "Packaging Arch Linux"
package --output-type pacman --package "$DIST/udm-$VERSION-1-x86_64.pkg.tar.xz" \
    --pacman-compression xz \
    --depends xcb-util-cursor --depends libxkbcommon-x11 \
    --depends libglvnd --depends fontconfig --depends dbus

echo "Done: $DIST"
