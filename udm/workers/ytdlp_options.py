"""yt-dlp option construction for captured streams and video pages."""

import logging
from pathlib import Path
import re
import shutil

from udm import paths

DEFAULT_QUALITY = "Best"
AUDIO_QUALITIES = {"audio", "audio only"}
OUTPUT_TEMPLATE = "%(title).150B [%(id)s].%(ext)s"
_BEST_FORMAT = "bv*+ba/b"
_HEIGHT = re.compile(r"(\d{3,4})p")


def format_for_quality(quality):
    """Return the yt-dlp format selector for a quality label.

    Accepts ``Best``, ``Audio Only`` (or ``audio``), and heights such as
    ``1080p``. Height selectors fall back to the best single file at or below
    that height when separate video and audio streams are unavailable.
    Unknown labels select the best quality.
    """
    label = str(quality or "").strip().lower()
    if label in AUDIO_QUALITIES:
        return "ba/b"
    match = _HEIGHT.fullmatch(label)
    if match:
        height = match.group(1)
        return f"bv*[height<={height}]+ba/b[height<={height}]/b"
    return _BEST_FORMAT


def is_audio_quality(quality):
    """Return whether ``quality`` requests audio only."""
    return str(quality or "").strip().lower() in AUDIO_QUALITIES


def ffmpeg_location():
    """Return the bundled FFmpeg binary, a system FFmpeg, or ``None``.

    The imageio-ffmpeg wheel ships a self-contained binary that survives app
    bundling, so it is preferred over a system install whose shared libraries
    may be missing on another Mac.
    """
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except (ImportError, RuntimeError, OSError):
        return shutil.which("ffmpeg")


def deno_location():
    """Return the Deno executable yt-dlp uses for JavaScript challenges.

    YouTube formats require solving JavaScript challenges. The app bundle
    ships Deno under ``deno/``; source runs use the ``deno`` wheel or a system
    install. Returns ``None`` when no runtime is available.
    """
    bundled = paths.resource_path("deno", "deno")
    if paths.is_frozen() and bundled.is_file():
        return str(bundled)
    try:
        import deno

        return deno.find_deno_bin()
    except (ImportError, OSError, RuntimeError):
        return shutil.which("deno")


def base_options(headers=None, proxy=None, deno=None):
    """Return options shared by downloads and format probes."""
    options = {
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "logger": logging.getLogger("udm.yt_dlp"),
        "http_headers": dict(headers or {}),
    }
    if proxy:
        options["proxy"] = proxy
    runtime = deno if deno is not None else deno_location()
    if runtime:
        options["js_runtimes"] = {"deno": {"path": runtime}}
    return options


def build_options(
    target_dir,
    headers=None,
    quality=DEFAULT_QUALITY,
    proxy=None,
    fragments=4,
    progress_hook=None,
    postprocessor_hook=None,
    ffmpeg=None,
    deno=None,
):
    """Return a yt-dlp parameter dictionary for one download.

    ``headers`` carry the captured browser session except cookies, which go
    into the downloader's cookie jar (see :mod:`udm.workers.ytdlp_cookies`).
    ``fragments`` bounds concurrent HLS or DASH fragment requests. Hooks
    receive yt-dlp status dictionaries on the worker thread.
    """
    options = base_options(headers, proxy, deno)
    options.update(
        {
            "outtmpl": {"default": str(Path(target_dir) / OUTPUT_TEMPLATE)},
            "format": format_for_quality(quality),
            # Within the chosen resolution prefer H.264 video and AAC audio,
            # which QuickTime and Finder preview play; AV1 and Opus often fail.
            "format_sort": ["res", "vcodec:h264", "acodec:aac"],
            "concurrent_fragment_downloads": max(1, min(int(fragments), 16)),
            "progress_hooks": [progress_hook] if progress_hook else [],
            "postprocessor_hooks": [postprocessor_hook] if postprocessor_hook else [],
        }
    )
    if not is_audio_quality(quality):
        options["merge_output_format"] = "mp4"
    location = ffmpeg if ffmpeg is not None else ffmpeg_location()
    if location:
        options["ffmpeg_location"] = location
    return options
