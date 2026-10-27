# PyInstaller build specification for UDM on macOS, Windows, and Linux.
# Run through the platform script in packaging/<platform>/, which supplies
# UDM_ICON (.icns on macOS, .ico on Windows; unset on Linux) and, on macOS,
# UDM_SAFARI_BIN (the compiled Safari extension binaries).
import os
from pathlib import Path
import sys

import deno
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

ROOT = Path(SPECPATH).resolve().parent
VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
ICON = os.environ.get("UDM_ICON") or None
# yt-dlp solves YouTube's JavaScript challenges with Deno and the challenge
# scripts shipped in yt-dlp-ejs; udm.workers.ytdlp_options finds deno/deno.
DENO = deno.find_deno_bin()
SAFARI_BIN = os.environ.get("UDM_SAFARI_BIN")

analysis = Analysis(
    [str(ROOT / "MACDM.py")],
    pathex=[str(ROOT)],
    binaries=[(DENO, "deno")],
    datas=collect_data_files("yt_dlp_ejs") + [
        (str(ROOT / "extension"), "extension"),
        (str(ROOT / "logo.png"), "."),
        (str(ROOT / "VERSION"), "."),
    ] + ([(SAFARI_BIN, "safari-bin")] if SAFARI_BIN else []),
    # The extractor modules are imported lazily by yt-dlp; its bundled
    # PyInstaller hook collects them, and imageio-ffmpeg's hook adds FFmpeg.
    # collect_submodules guards against imports static analysis cannot see,
    # such as the lazy exports in udm.workers.
    hiddenimports=collect_submodules("udm")
    + ["PyQt6.QtNetwork", "PyQt6.QtSvg", "truststore", "yt_dlp_ejs", "libtorrent"],
    excludes=["tkinter"],
    noarchive=False,
)
pyz = PYZ(analysis.pure)
executable = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="UDM",
    icon=ICON,
    console=False,
    argv_emulation=False,
    target_arch=None,
)
collected = COLLECT(
    executable,
    analysis.binaries,
    analysis.datas,
    name="UDM",
)
if sys.platform == "darwin":
    app = BUNDLE(
        collected,
        name="UDM.app",
        icon=ICON,
        bundle_identifier="com.udm.manager",
        version=VERSION,
        info_plist={
            "CFBundleName": "UDM",
            "CFBundleDisplayName": "UDM",
            "CFBundleShortVersionString": VERSION,
            "CFBundleVersion": VERSION,
            # The libtorrent wheel is built for macOS 15 and later.
            "LSMinimumSystemVersion": "15.0",
            "NSHighResolutionCapable": True,
            "NSHumanReadableCopyright": "Umbrella Download Manager",
            # Clicking a magnet link or opening a .torrent file hands it to UDM
            # (udm.ui.open_events).
            "CFBundleURLTypes": [
                {"CFBundleURLName": "Magnet link", "CFBundleURLSchemes": ["magnet"]},
            ],
            "CFBundleDocumentTypes": [
                {
                    "CFBundleTypeName": "BitTorrent file",
                    "CFBundleTypeRole": "Viewer",
                    "LSHandlerRank": "Alternate",
                    "LSItemContentTypes": ["org.bittorrent.torrent"],
                    "CFBundleTypeExtensions": ["torrent"],
                },
            ],
        },
    )
