"""HTTP download worker with optional segmented transfers."""

import logging
from pathlib import Path
import re
import threading
import time

from PyQt6.QtCore import QThread, pyqtSignal
import requests


class DownloadError(Exception):
    """Report a remote response that cannot produce a valid download."""


class DownloadWorker(QThread):
    """Download one URL without blocking the Qt event loop."""

    progress = pyqtSignal(str, int, int, str, str, str)
    completed = pyqtSignal(str, bool, str)

    def __init__(
        self,
        download_id,
        url,
        save_path,
        segments=8,
        proxy=None,
        session=None,
    ):
        super().__init__()
        self.download_id = download_id
        self.url = url
        self.save_path = Path(save_path)
        self.segments = segments
        self.proxy = proxy
        self.session = session or requests.Session()
        self._paused = False
        self._cancelled = False

    def run(self):
        """Select segmented or streaming transfer based on server capabilities."""
        proxies = {"http": self.proxy, "https": self.proxy} if self.proxy else None
        headers = {"User-Agent": "Mozilla/5.0"}
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
            for path in part_paths:
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

    def _wait_while_paused(self):
        while self._paused and not self._cancelled:
            self.msleep(100)

    def _emit_progress(self, downloaded, total, started):
        elapsed = max(time.monotonic() - started, 0.001)
        rate = downloaded / elapsed
        remaining = max(total - downloaded, 0) if total else 0
        eta = self._format_duration(remaining / rate) if total and rate else "--"
        self.progress.emit(
            self.download_id,
            downloaded,
            total,
            self._format_rate(rate),
            eta,
            "Downloading",
        )

    @staticmethod
    def _format_rate(bytes_per_second):
        units = ("B/s", "KB/s", "MB/s", "GB/s")
        value = float(bytes_per_second)
        for unit in units[:-1]:
            if value < 1024:
                return f"{value:.1f} {unit}"
            value /= 1024
        return f"{value:.1f} {units[-1]}"

    @staticmethod
    def _format_duration(seconds):
        seconds = max(0, int(seconds))
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

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
