"""HTTP download worker with optional segmented transfers."""

import logging
from pathlib import Path
import threading

from PyQt6.QtCore import QThread, pyqtSignal
import requests


class DownloadWorker(QThread):
    """Download one URL without blocking the Qt event loop."""

    progress = pyqtSignal(str, int, str, str)
    completed = pyqtSignal(str, bool, str)

    def __init__(self, download_id, url, save_path, segments=8, proxy=None):
        super().__init__()
        self.download_id = download_id
        self.url = url
        self.save_path = Path(save_path)
        self.segments = segments
        self.proxy = proxy
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
            response = requests.head(
                self.url,
                headers=headers,
                proxies=proxies,
                allow_redirects=True,
                timeout=10,
            )
            response.raise_for_status()
            file_size = int(response.headers.get("content-length", 0))
            accepts_ranges = response.headers.get("accept-ranges", "none") != "none"
            return file_size, accepts_ranges
        except (requests.RequestException, TypeError, ValueError):
            return 0, False

    def _download_stream(self, headers, proxies, file_size):
        try:
            response = requests.get(
                self.url,
                headers=headers,
                proxies=proxies,
                stream=True,
                timeout=15,
            )
            response.raise_for_status()
            self.save_path.parent.mkdir(parents=True, exist_ok=True)
            downloaded = 0
            with self.save_path.open("wb") as target:
                for chunk in response.iter_content(chunk_size=8192):
                    if self._cancelled:
                        self._remove_partial(self.save_path)
                        return
                    self._wait_while_paused()
                    if chunk:
                        target.write(chunk)
                        downloaded += len(chunk)
                        percentage = int(downloaded / file_size * 100) if file_size else 0
                        self.progress.emit(
                            self.download_id,
                            percentage,
                            "Active",
                            "Downloading",
                        )
            self.completed.emit(self.download_id, True, "Completed")
        except (OSError, requests.RequestException) as error:
            self.completed.emit(self.download_id, False, str(error))

    def _download_segmented(self, headers, proxies, file_size):
        # The final segment absorbs the remainder so integer division cannot
        # leave trailing bytes unrequested.
        part_size = file_size // self.segments
        part_paths = [
            Path(f"{self.save_path}.part{index}") for index in range(self.segments)
        ]
        errors = []
        threads = []

        self.save_path.parent.mkdir(parents=True, exist_ok=True)
        for index, part_path in enumerate(part_paths):
            start = index * part_size
            end = file_size - 1 if index == self.segments - 1 else start + part_size - 1
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
            percentage = min(100, int(downloaded / file_size * 100))
            self.progress.emit(
                self.download_id,
                percentage,
                f"{self.segments} Segments",
                "Downloading",
            )

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
            self.completed.emit(self.download_id, True, "Completed")
        except OSError as error:
            self.completed.emit(self.download_id, False, str(error))

    def _download_part(self, headers, proxies, start, end, part_path, errors):
        part_headers = dict(headers)
        part_headers["Range"] = f"bytes={start}-{end}"
        try:
            response = requests.get(
                self.url,
                headers=part_headers,
                proxies=proxies,
                stream=True,
                timeout=15,
            )
            response.raise_for_status()
            with part_path.open("wb") as target:
                for chunk in response.iter_content(chunk_size=8192):
                    if self._cancelled:
                        return
                    self._wait_while_paused()
                    if chunk:
                        target.write(chunk)
        except (OSError, requests.RequestException) as error:
            logging.error("Segment download error: %s", error)
            errors.append(error)

    def _wait_while_paused(self):
        while self._paused and not self._cancelled:
            self.msleep(100)

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
