"""Tests for link extraction and streaming download behavior."""

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from bs4 import BeautifulSoup

from udm.workers.download import DownloadWorker
from udm.workers.spiders import SpiderWorker


class FakeResponse:
    def __init__(self, chunks=None, headers=None):
        self.chunks = chunks or []
        self.headers = headers or {}

    def raise_for_status(self):
        return None

    def iter_content(self, chunk_size):
        yield from self.chunks


class SpiderWorkerTests(unittest.TestCase):
    def test_extract_links_resolves_and_deduplicates_media(self):
        html = """
        <html><body>
          <img src="/image.png">
          <video><source src="movie.mp4"></video>
          <a href="/manual.pdf">Manual</a>
          <a href="/manual.pdf">Duplicate</a>
          <a href="/page">Page</a>
        </body></html>
        """
        worker = SpiderWorker("https://example.com/base/")
        links = worker.extract_links(BeautifulSoup(html, "html.parser"))
        self.assertEqual(
            links,
            [
                "https://example.com/base/movie.mp4",
                "https://example.com/image.png",
                "https://example.com/manual.pdf",
            ],
        )


class DownloadWorkerTests(unittest.TestCase):
    def test_stream_download_writes_content_and_emits_completion(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "file.bin"
            worker = DownloadWorker(
                "download-1",
                "https://example.com/file.bin",
                target,
                segments=1,
            )
            completions = []
            worker.completed.connect(
                lambda download_id, success, message: completions.append(
                    (download_id, success, message)
                )
            )
            head = FakeResponse(headers={"content-length": "6"})
            stream = FakeResponse(chunks=[b"abc", b"def"])
            with patch("udm.workers.download.requests.head", return_value=head):
                with patch(
                    "udm.workers.download.requests.get",
                    return_value=stream,
                ):
                    worker.run()
            self.assertEqual(target.read_bytes(), b"abcdef")
            self.assertEqual(
                completions,
                [("download-1", True, "Completed")],
            )


if __name__ == "__main__":
    unittest.main()
