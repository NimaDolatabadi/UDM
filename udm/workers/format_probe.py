"""List the qualities yt-dlp can download for a page or stream.

Runs without Qt so the native host can answer quality requests directly,
without waiting on (or starting) the desktop application.
"""

import logging

from udm.workers.ytdlp_cookies import load_cookies
from udm.workers.ytdlp_options import base_options


def probe_qualities(request, proxy=None, downloader_factory=None):
    """Return ``{"ok", "title", "qualities"}`` for a stream request.

    Each quality has ``quality`` (sent back with the download request),
    ``label``, and ``detail`` (container and approximate size). The list
    starts with the best quality, then each video height from highest to
    lowest, then audio only. Failures return ``ok: False`` with a short error.
    """
    options = base_options(request.stream_headers(), proxy)
    options["skip_download"] = True
    try:
        with _create(options, downloader_factory) as downloader:
            jar = getattr(downloader, "cookiejar", None)
            if jar is not None:
                load_cookies(jar, request.url, request.cookie_jar, request.cookies)
            info = downloader.extract_info(request.url, download=False)
    except Exception as error:  # yt-dlp raises many unrelated types.
        logging.warning("Quality probe failed for %s: %s", request.url, error)
        return {"ok": False, "error": _short_error(error)}
    if info.get("_type") == "playlist" and info.get("entries"):
        info = next((entry for entry in info["entries"] if entry), info)
    return {
        "ok": True,
        "title": info.get("title") or "",
        "qualities": qualities_from_formats(info.get("formats") or [info], info.get("duration")),
    }


def qualities_from_formats(formats, duration=None):
    """Summarize yt-dlp format records into user-facing quality choices.

    Sizes come from the reported file size, or are estimated from bitrate and
    ``duration`` (seconds) for formats such as HLS that report no size.
    """
    audio = [item for item in formats if _is_audio_only(item)]
    best_audio = max(audio, key=lambda item: item.get("abr") or item.get("tbr") or 0, default=None)
    audio_size = _size(best_audio, duration) if best_audio else 0
    by_height = {}
    for item in formats:
        height = item.get("height")
        if not height or item.get("vcodec") in (None, "none"):
            continue
        current = by_height.get(height)
        if current is None or (item.get("tbr") or 0) > (current.get("tbr") or 0):
            by_height[height] = item
    choices = [{"quality": "best", "label": "Best quality", "detail": "Highest available"}]
    for height in sorted(by_height, reverse=True):
        item = by_height[height]
        # Video-only formats are merged with the best audio track.
        extra = audio_size if item.get("acodec") in (None, "none") else 0
        choices.append(
            {
                "quality": f"{height}p",
                "label": f"{height}p",
                "detail": _detail("MP4", _size(item, duration) + extra),
            }
        )
    if best_audio is not None:
        extension = (best_audio.get("ext") or "audio").upper()
        choices.append(
            {"quality": "audio", "label": "Audio only", "detail": _detail(extension, audio_size)}
        )
    return choices


def _create(options, factory):
    if factory is not None:
        return factory(options)
    from yt_dlp import YoutubeDL

    return YoutubeDL(options)


def _is_audio_only(item):
    return item.get("vcodec") == "none" and item.get("acodec") not in (None, "none")


def _size(item, duration=None):
    reported = item.get("filesize") or item.get("filesize_approx")
    if reported:
        return int(reported)
    bitrate = item.get("tbr") or item.get("vbr") or item.get("abr")
    # Bitrates are in kilobits per second: 1 kbit/s is 125 bytes per second.
    return int(bitrate * duration * 125) if bitrate and duration else 0


def _detail(container, size):
    if not size:
        return container
    megabytes = size / (1024 * 1024)
    text = f"{megabytes / 1024:.1f} GB" if megabytes >= 1024 else f"{megabytes:.0f} MB"
    return f"{container} - about {text}"


def _short_error(error):
    text = str(error).replace("ERROR: ", "").strip()
    return text.splitlines()[0][:200] if text else type(error).__name__
