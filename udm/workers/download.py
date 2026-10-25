"""HTTP download worker with optional segmented transfers."""

import logging
from pathlib import Path
import re
import threading
import time

from PyQt6.QtCore import QThread, pyqtSignal
import requests

from udm.filenames import claim_unique_path, remote_filename
from udm.workers.formatting import format_duration, format_rate


class DownloadError(Exception):
    """Report a remote response that cannot produce a valid download."""


class DownloadWorker(QThread):
    """Download one URL without blocking the Qt event loop.

    With a ``router`` (a callable mapping a filename to its category
    directory), the worker adopts the server-reported filename before writing
    and emits ``relocated`` with the new destination path.
    """

    progress = pyqtSignal(str, int, int, str, str, str)
    completed = pyqtSignal(str, bool, str)
    relocated = pyqtSignal(str, str)

    def __init__(
        self,
        download_id,
        url,
        save_path,
        segments=8,
        proxy=None,
        session=None,
        headers=None,
        router=None,
    ):
        super().__init__()
        self.download_id = download_id
        self.url = url
        self.save_path = Path(save_path)
        self.segments = segments
        self.proxy = proxy
        self.session = session or requests.Session()
        # Captured browser headers (cookies, referrer, user agent) override the
        # generic defaults so session-bound links stay authorized.
        self.headers = {"User-Agent": "Mozilla/5.0", **(headers or {})}
        self.router = router
        self._name_resolved = False
        self._paused = False
        self._cancelled = False

    def run(self):
        """Select segmented or streaming transfer based on server capabilities."""
        proxies = {"http": self.proxy, "https": self.proxy} if self.proxy else None
        headers = dict(self.headers)
        file_size, accepts_ranges = self._inspect_remote(headers, proxies)

        if file_size and accepts_ranges and self.segments > 1:
            self._download_segmented(headers, proxies, file_size)
        else:
            self._download_stream(headers, proxies, file_size)

    def _inspect_remote(self, headers, proxies):
        try:
            response = self.session.head(
                self.url,
                headers=headers,
                proxies=proxies,
                allow_redirects=True,
                timeout=10,
            )
            response.raise_for_status()
            self._adopt_remote_name(response)
            file_size = max(0, int(response.headers.get("content-length", 0)))
            accepts_ranges = (
                response.headers.get("accept-ranges", "none").lower() == "bytes"
            )
            return file_size, accepts_ranges
        except (requests.RequestException, TypeError, ValueError):
            return 0, False

    def _download_stream(self, headers, proxies, file_size):
        try:
            response = self.session.get(
                self.url,
                headers=headers,
                proxies=proxies,
                stream=True,
                timeout=15,
            )
            response.raise_for_status()
            self._adopt_remote_name(response)
            self.save_path.parent.mkdir(parents=True, exist_ok=True)
            downloaded = 0
            started = time.monotonic()
            with self.save_path.open("wb") as target:
                for chunk in response.iter_content(chunk_size=8192):
                    if self._cancelled:
                        self._remove_partial(self.save_path)
                        return
                    self._wait_while_paused()
                    if chunk:
                        target.write(chunk)
                        downloaded += len(chunk)
                        self._emit_progress(downloaded, file_size, started)
            if file_size and downloaded != file_size:
                self._remove_partial(self.save_path)
                raise DownloadError(
                    f"Size mismatch: expected {file_size} bytes, "
                    f"received {downloaded}"
                )
            self.completed.emit(self.download_id, True, "Completed")
        except (DownloadError, OSError, requests.RequestException) as error:
            self.completed.emit(self.download_id, False, str(error))

    def _download_segmented(self, headers, proxies, file_size):
        # The final segment absorbs the remainder so integer division cannot
        # leave trailing bytes unrequested.
        segment_count = min(self.segments, file_size)
        part_size = file_size // segment_count
        part_paths = [
            Path(f"{self.save_path}.part{index}") for index in range(segment_count)
        ]
        errors = []
        threads = []
        started = time.monotonic()

        self.save_path.parent.mkdir(parents=True, exist_ok=True)
        for index, part_path in enumerate(part_paths):
            start = index * part_size
            end = (
                file_size - 1
                if index == segment_count - 1
                else start + part_size - 1
            )
            thread = threading.Thread(
                target=self._download_part,
                args=(headers, proxies, start, end, part_path, errors),
                daemon=True,
            )
            thread.start()
            threads.append(thread)

        while any(thread.is_alive() for thread in threads):
            if self._cancelled:
                break
            self.msleep(100)
            downloaded = sum(
                path.stat().st_size for path in part_paths if path.exists()
            )
            if not self._paused:
                self._emit_progress(downloaded, file_size, started)

        for thread in threads:
            # Assembly must not begin until every part file has been closed.
            thread.join()

        if self._cancelled or errors:
            # Also drop an empty destination claimed by _adopt_remote_name.
            for path in (*part_paths, self.save_path):
                self._remove_partial(path)
            if errors:
                self.completed.emit(self.download_id, False, str(errors[0]))
            return

        try:
            with self.save_path.open("wb") as target:
                for path in part_paths:
                    with path.open("rb") as source:
                        for chunk in iter(lambda: source.read(1024 * 1024), b""):
                            target.write(chunk)
                    path.unlink()
            assembled_size = self.save_path.stat().st_size
            if assembled_size != file_size:
                self._remove_partial(self.save_path)
                raise DownloadError(
                    f"Size mismatch: expected {file_size} bytes, "
                    f"assembled {assembled_size}"
                )
            self.completed.emit(self.download_id, True, "Completed")
        except (DownloadError, OSError) as error:
            self.completed.emit(self.download_id, False, str(error))

    def _download_part(self, headers, proxies, start, end, part_path, errors):
        part_headers = dict(headers)
        part_headers["Range"] = f"bytes={start}-{end}"
        try:
            response = self.session.get(
                self.url,
                headers=part_headers,
                proxies=proxies,
                stream=True,
                timeout=15,
            )
            response.raise_for_status()
            expected = end - start + 1
            content_range = response.headers.get("content-range", "")
            match = re.fullmatch(r"bytes (\d+)-(\d+)/(\d+|\*)", content_range)
            if (
                response.status_code != 206
                or not match
                or (int(match.group(1)), int(match.group(2))) != (start, end)
            ):
                raise DownloadError(
                    f"Server rejected byte range {start}-{end}"
                )
            downloaded = 0
            with part_path.open("wb") as target:
                for chunk in response.iter_content(chunk_size=8192):
                    if self._cancelled:
                        return
                    self._wait_while_paused()
                    if chunk:
                        target.write(chunk)
                        downloaded += len(chunk)
            if downloaded != expected:
                raise DownloadError(
                    f"Segment {start}-{end} was {downloaded} bytes; "
                    f"expected {expected}"
                )
        except (DownloadError, OSError, requests.RequestException) as error:
            logging.error("Segment download error: %s", error)
            errors.append(error)

    def _adopt_remote_name(self, response):
        # Links such as "download?id=1" reveal the real name (and therefore the
        # category folder) only in the response, so re-route before writing.
        if self.router is None or self._name_resolved:
            return
        self._name_resolved = True
        final_url = getattr(response, "url", None) or self.url
        name = remote_filename(final_url, response.headers, self.save_path.name)
        if not name or name == self.save_path.name:
            return
        try:
            self.save_path = claim_unique_path(self.router(name), name)
        except OSError as error:
            logging.warning("Keeping original destination: %s", error)
            return
        self.relocated.emit(self.download_id, str(self.save_path))

    def _wait_while_paused(self):
        while self._paused and not self._cancelled:
            self.msleep(100)

    def _emit_progress(self, downloaded, total, started):
        elapsed = max(time.monotonic() - started, 0.001)
        rate = downloaded / elapsed
        remaining = max(total - downloaded, 0) if total else 0
        eta = format_duration(remaining / rate) if total and rate else "--"
        self.progress.emit(
            self.download_id,
            downloaded,
            total,
            format_rate(rate),
            eta,
            "Downloading",
        )

    @staticmethod
    def _remove_partial(path):
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass

    def pause(self):
        """Pause transfer loops without terminating the worker thread."""
        self._paused = True

    def resume(self):
        """Resume a worker paused by the queue controller."""
        self._paused = False

    def cancel(self):
        """Request cancellation and release any paused transfer loop."""
        self._cancelled = True
        self._paused = False
