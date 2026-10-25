# Packaging and Releases

UDM is frozen with PyInstaller from one cross-platform spec,
`packaging/udm.spec`, and packaged per platform:

| Platform | Script | Output in `dist/` |
| -------- | ------ | ----------------- |
| macOS | `packaging/macos/build_dmg.sh` | `UDM-<version>-macos-<arch>.dmg` |
| Windows | `packaging/windows/build_installer.ps1` | `UDM-<version>-windows-x64-setup.exe`, `UDM-<version>-windows-x64.zip` |
| Linux | `packaging/linux/build_packages.sh` | `udm_<version>_amd64.deb`, `udm-<version>-1.x86_64.rpm`, `udm-<version>-1-x86_64.pkg.tar.xz` (Arch), `UDM-<version>-linux-x86_64.tar.gz` |

Each script builds on its own platform; PyInstaller does not cross-compile.

## Publishing a Release

`.github/workflows/release.yml` builds every package on GitHub-hosted runners
(macOS 15 arm64 and Intel, Windows Server 2022, Ubuntu 22.04) and publishes
them as a GitHub release:

1. Bump `VERSION` and add the `PROJECT_LOG.md` entry, then push to `main`.
2. Tag the commit and push the tag:
   `git tag v<version> && git push origin v<version>`.
3. The workflow checks that the tag matches `VERSION`, builds all packages,
   and creates the release with the log entry as release notes and a
   `SHA256SUMS.txt` file.

Running the workflow by hand (Actions > Release > Run workflow) builds the
packages as downloadable workflow artifacts without publishing a release.
`.github/workflows/ci.yml` runs the unit tests on Ubuntu and macOS for every
push to `main` and every pull request.

## macOS

### Requirements

- macOS 15 or later (the libtorrent wheel's minimum, which the bundle also
  declares); the bundle targets the build machine's architecture.
- The project dependencies plus PyInstaller:
  `pip install -r packaging/requirements-build.txt`.
- `sips`, `iconutil`, `codesign`, and `hdiutil`, which ship with macOS.

### Building

```bash
conda run -n mine packaging/macos/build_dmg.sh
```

The script:

1. renders `logo.png` into an `.icns` icon;
2. runs PyInstaller with `packaging/udm.spec`, bundling the `udm`
   package, the `extension/` source, `logo.png`, `VERSION`, yt-dlp with its
   extractors and the `yt-dlp-ejs` challenge scripts, the Deno runtime used
   for YouTube, truststore, libtorrent, and the imageio-ffmpeg FFmpeg binary,
   and registers the `magnet` URL scheme and `.torrent` document type;
3. re-signs the bundle ad hoc so Apple silicon accepts the nested binaries;
4. writes `dist/UDM-<version>-macos-<arch>.dmg` containing `UDM.app` and an
   `Applications` shortcut.

Intermediate files go to `build/macos/`. Both `build/` and `dist/` are ignored
by Git.

### Installing the DMG

Open the disk image and drag UDM into Applications. The build is not signed
with an Apple Developer ID, so Gatekeeper blocks the first launch. Either
Control-click UDM in Applications and choose Open, or run:

```bash
xattr -dr com.apple.quarantine /Applications/UDM.app
```

## Windows

Requires Python with `packaging/requirements-build.txt`, Pillow (to convert
`logo.png` to an `.ico`), and Inno Setup 6. Run
`pwsh packaging/windows/build_installer.ps1`. The installer installs per user
or for all users, adds a Start menu entry, and optionally a desktop icon; the
zip is a portable copy of the same folder. The executables are not
code-signed, so SmartScreen warns on first launch (More info > Run anyway).

## Linux

Requires Python with `packaging/requirements-build.txt`, `fpm`, `rpmbuild`
(the `rpm` package on Debian and Ubuntu), and `bsdtar` (`libarchive-tools`).
Run `packaging/linux/build_packages.sh`. Every package installs the
PyInstaller folder to `/opt/udm`, a `udm` command in `/usr/bin`, a desktop
entry, and an icon, and depends on the system libraries Qt's xcb plugin needs
(`xcb-util-cursor`, `libxkbcommon-x11`, EGL, fontconfig, D-Bus). Build on the
oldest supported glibc (Ubuntu 22.04 in CI) so the packages run on newer
distributions.

```bash
sudo apt install ./udm_<version>_amd64.deb          # Debian, Ubuntu
sudo dnf install ./udm-<version>-1.x86_64.rpm       # Fedora, RHEL
sudo pacman -U ./udm-<version>-1-x86_64.pkg.tar.xz  # Arch Linux
```

## Runtime Locations

On Windows the data directory is `%APPDATA%\UDM`; on Linux it is
`$XDG_DATA_HOME/UDM` (default `~/.local/share/UDM`). The macOS locations are:

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
  matches only the build machine's architecture, so releases ship one DMG per
  architecture.
- TODO: Port the browser bridge to Windows and Linux: native-host manifests
  in the registry and in the Linux browser directories, and a named-pipe
  client on Windows, where Python has no Unix sockets. The extension installer
  and magnet or `.torrent` file associations are macOS-only today.
- TODO: Sign the Windows executables and installer.
