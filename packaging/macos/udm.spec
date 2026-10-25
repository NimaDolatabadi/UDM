# PyInstaller build specification for the UDM macOS application bundle.
# Run through packaging/macos/build_dmg.sh, which supplies UDM_ICNS.
import os
from pathlib import Path

import deno
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

ROOT = Path(SPECPATH).resolve().parents[1]
VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
ICON = os.environ.get("UDM_ICNS") or None
# yt-dlp solves YouTube's JavaScript challenges with Deno and the challenge
# scripts shipped in yt-dlp-ejs; udm.workers.ytdlp_options finds deno/deno.
DENO = deno.find_deno_bin()

analysis = Analysis(
    [str(ROOT / "MACDM.py")],
    pathex=[str(ROOT)],
    binaries=[(DENO, "deno")],
    datas=collect_data_files("yt_dlp_ejs") + [
        (str(ROOT / "extension"), "extension"),
        (str(ROOT / "logo.png"), "."),
        (str(ROOT / "VERSION"), "."),
    ],
    # The extractor modules are imported lazily by yt-dlp; its bundled
    # PyInstaller hook collects them, and imageio-ffmpeg's hook adds FFmpeg.
    # collect_submodules guards against imports static analysis cannot see,
    # such as the lazy exports in udm.workers.
    hiddenimports=collect_submodules("udm")
    + ["PyQt6.QtNetwork", "PyQt6.QtSvg", "truststore", "yt_dlp_ejs"],
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
        "LSMinimumSystemVersion": "11.0",
        "NSHighResolutionCapable": True,
        "NSHumanReadableCopyright": "Umbrella Download Manager",
    },
)
