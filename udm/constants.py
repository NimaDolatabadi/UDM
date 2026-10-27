"""Shared application defaults and immutable choices."""

SCHEDULE_COLORS = ["#ff4d4d", "#ffad33", "#2eb82e", "#3399ff", "#b366ff"]
RECURRENCE_OPTIONS = ["Every Day", "Even Days", "Odd Days"]
STREAM_QUALITY_OPTIONS = ["Best", "1080p", "720p", "480p", "Audio Only"]

DEFAULT_CONFIG = {
    "language": "English",
    "theme": "System",
    "proxy": "",
    "dns": "",
    "segments": 8,
    "max_concurrent": 4,
    "stream_quality": "Best",
    # Single new downloads open a prompt for the folder and Start Now or
    # Download Later.
    "confirm_new_downloads": True,
    # Without the prompt, captures are added paused unless this is enabled.
    "capture_autostart": False,
    # Empty means the user's Downloads folder; categories are created inside.
    "download_dir": "",
    "start_with_os": False,
    "start_minimized": False,
    "close_to_tray": True,
    "clipboard_monitor": False,
    "sound_on_complete": False,
    "schedules": [
        {
            "name": "Default Schedule",
            "active": False,
            "max_dl": 2,
            "start_time": "00:00",
            "end_time": "06:00",
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
            "recurrence": "Every Day",
            "color": SCHEDULE_COLORS[0],
            "is_default": True,
        }
    ],
    "categories": {
        "Compressed": "zip, rar, gz, tar, 7z, bz2",
        "Documents": "pdf, doc, docx, txt, ppt, pptx, xls, xlsx, odt, rtf",
        "Music": "mp3, wav, flac, aac, ogg, m4a",
        "Programs/Windows": "exe, msi, bat, cmd",
        "Programs/Linux": "deb, rpm, sh, AppImage, run, bin",
        "Programs/Mac": "dmg, pkg",
        "Videos": "mp4, mkv, avi, mov, wmv, flv, webm",
        "Android": "apk, xapk, apks, obb",
        "Torrents": "torrent",
    },
}

DOWNLOAD_EXTENSIONS = (
    ".zip",
    ".rar",
    ".mp4",
    ".mp3",
    ".pdf",
    ".exe",
    ".dmg",
    ".pkg",
    ".iso",
    ".mkv",
    ".7z",
    ".gz",
    ".tar",
)

SPIDER_EXTENSIONS = (
    ".zip",
    ".rar",
    ".exe",
    ".pdf",
    ".mp4",
    ".mp3",
    ".dmg",
    ".pkg",
    ".apk",
    ".sh",
)
