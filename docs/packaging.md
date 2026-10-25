# macOS Packaging

UDM ships for macOS as `UDM.app` inside a drag-to-install disk image.

## Requirements

- macOS 15 or later (the libtorrent wheel's minimum, which the bundle also
  declares); the bundle targets the build machine's architecture.
- The project dependencies plus PyInstaller:
  `pip install -r packaging/requirements-build.txt`.
- `sips`, `iconutil`, `codesign`, and `hdiutil`, which ship with macOS.

## Building

```bash
conda run -n mine packaging/macos/build_dmg.sh
```

The script:

1. renders `logo.png` into an `.icns` icon;
2. runs PyInstaller with `packaging/macos/udm.spec`, bundling the `udm`
   package, the `extension/` source, `logo.png`, `VERSION`, yt-dlp with its
   extractors and the `yt-dlp-ejs` challenge scripts, the Deno runtime used
   for YouTube, truststore, libtorrent, and the imageio-ffmpeg FFmpeg binary,
   and registers the `magnet` URL scheme and `.torrent` document type;
3. re-signs the bundle ad hoc so Apple silicon accepts the nested binaries;
4. writes `dist/UDM-<version>.dmg` containing `UDM.app` and an
   `Applications` shortcut.

Intermediate files go to `build/macos/`. Both `build/` and `dist/` are ignored
by Git.

## Installing the DMG

Open the disk image and drag UDM into Applications. The build is not signed
with an Apple Developer ID, so Gatekeeper blocks the first launch. Either
Control-click UDM in Applications and choose Open, or run:

```bash
xattr -dr com.apple.quarantine /Applications/UDM.app
```

## Runtime Locations

| Purpose | Path |
| ------- | ---- |
| Settings | `~/Library/Application Support/UDM/udm_config.json` |
| Logs | `~/Library/Application Support/UDM/logs/` |
| Bridge socket | `~/Library/Application Support/UDM/bridge.sock` |
| Installed extension | `~/Library/Application Support/UDM/extension/` |
| Torrent resume data | `~/Library/Application Support/UDM/torrents/` |
| Downloads | `~/Downloads/<category>/` (Options > General > Download folder) |

`UDM_DATA_DIR` overrides the data directory for development and tests. A
source checkout's legacy `udm_config.json` in the working directory is copied
there on first launch.

## Future Work

- TODO: Sign with a Developer ID certificate and notarize with `notarytool`
  so Gatekeeper accepts the first launch. This is also required before an App
  Store or Safari-extension release.
- TODO: Build a universal (arm64 and x86_64) bundle; the current FFmpeg wheel
  matches only the build machine's architecture.
