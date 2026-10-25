"""Stream and video-page download worker backed by yt-dlp."""

import glob
import logging
from pathlib import Path
import time

from PyQt6.QtCore import QThread, pyqtSignal

from udm.workers.formatting import format_duration, format_rate
from udm.workers.ytdlp_cookies import load_cookies
from udm.workers.ytdlp_options import DEFAULT_QUALITY, build_options


class _Cancelled(Exception):
    """Abort yt-dlp from inside a progress hook."""


class StreamWorker(QThread):
    """Resolve and download one stream or page URL without blocking Qt.

    Emits the same ``progress`` and ``completed`` signals as
    :class:`~udm.workers.download.DownloadWorker`, plus ``renamed`` once the
    media title is known so the queue can replace its placeholder label.
    """

    progress = pyqtSignal(str, int, int, str, str, str)
    completed = pyqtSignal(str, bool, str)
    renamed = pyqtSignal(str, str)

    def __init__(
        self,
        download_id,
        url,
        target_dir,
        headers=None,
        quality=DEFAULT_QUALITY,
        proxy=None,
        fragments=4,
        downloader_factory=None,
        cookie_jar=(),
        cookie_header="",
    ):
        super().__init__()
        self.download_id = download_id
        self.url = url
        self.target_dir = Path(target_dir)
        self.headers = dict(headers or {})
        self.quality = quality
        self.proxy = proxy
        self.fragments = fragments
        self._factory = downloader_factory
        self.cookie_jar = tuple(cookie_jar)
        self.cookie_header = cookie_header
        self._paused = False
        self._cancelled = False
        self._title_sent = False
        self._partials = set()

    def run(self):
        """Download the URL and report completion, failure, or cancellation."""
        self.target_dir.mkdir(parents=True, exist_ok=True)
        options = build_options(
            self.target_dir,
            headers=self.headers,
            quality=self.quality,
            proxy=self.proxy,
            fragments=self.fragments,
            progress_hook=self._on_progress,
            postprocessor_hook=self._on_postprocess,
        )
        try:
            with self._create_downloader(options) as downloader:
                downloader.download([self.url])
        except Exception as error:  # yt-dlp wraps failures in many types.
            if self._cancelled:
                self._remove_partials()
                return
            logging.error("Stream download error: %s", error)
            self.completed.emit(self.download_id, False, _short_error(error))
            return
        if self._cancelled:
            self._remove_partials()
            return
        self.completed.emit(self.download_id, True, "Completed")

    def _create_downloader(self, options):
        if self._factory is not None:
            downloader = self._factory(options)
        else:
            # Imported lazily: yt-dlp is large and only needed for stream rows.
            from yt_dlp import YoutubeDL

            downloader = YoutubeDL(options)
        jar = getattr(downloader, "cookiejar", None)
        if jar is not None:
            load_cookies(jar, self.url, self.cookie_jar, self.cookie_header)
        return downloader

    def _on_progress(self, status):
        if self._cancelled:
            raise _Cancelled()
        # Blocking the hook pauses yt-dlp between chunks and fragments.
        while self._paused and not self._cancelled:
            time.sleep(0.1)
        if self._cancelled:
            raise _Cancelled()
        self._remember_partial(status)
        self._announce_title(status.get("info_dict") or {})
        if status.get("status") != "downloading":
            return
        downloaded = int(status.get("downloaded_bytes") or 0)
        total = int(
            status.get("total_bytes") or status.get("total_bytes_estimate") or 0
        )
        speed = status.get("speed") or 0
        eta = status.get("eta")
        self.progress.emit(
            self.download_id,
            downloaded,
            total,
            format_rate(speed),
            format_duration(eta),
            "Downloading",
        )

    def _on_postprocess(self, status):
        if status.get("status") == "started":
            self.progress.emit(
                self.download_id, 0, 0, "--", "--", "Processing"
            )

    def _announce_title(self, info):
        title = info.get("title")
        if title and not self._title_sent:
            self._title_sent = True
            self.renamed.emit(self.download_id, str(title))

    def _remember_partial(self, status):
        for key in ("tmpfilename", "filename"):
            if status.get(key):
                self._partials.add(Path(status[key]))

    def _remove_partials(self):
        # yt-dlp derives .part, .ytdl, and HLS/DASH "-FragN" files from the
        # output name, so remove everything sharing that prefix.
        for path in self._partials:
            for candidate in path.parent.glob(f"{glob.escape(path.name)}*"):
                try:
                    candidate.unlink(missing_ok=True)
                except OSError:
                    pass

    def pause(self):
        """Hold the transfer at the next progress callback."""
        self._paused = True

    def resume(self):
        """Release a transfer held by :meth:`pause`."""
        self._paused = False

    def cancel(self):
        """Abort at the next progress callback and remove partial files."""
        self._cancelled = True
        self._paused = False


def _short_error(error):
    text = str(error).replace("ERROR: ", "").strip()
    return text.splitlines()[0][:200] if text else type(error).__name__

