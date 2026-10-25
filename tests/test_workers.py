"""Tests for link extraction and streaming download behavior."""

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from bs4 import BeautifulSoup
import requests

from udm.workers.download import DownloadWorker
from udm.workers.spiders import SpiderWorker


class FakeResponse:
    def __init__(self, chunks=None, headers=None, status_code=200, url=None):
        self.chunks = chunks or []
        self.headers = headers or {}
        self.status_code = status_code
        self.url = url

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
    @staticmethod
    def _session(head, gets):
        session = Mock()
        session.head.return_value = head
        session.get.side_effect = gets
        return session

    def test_stream_download_writes_content_and_emits_completion(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "file.bin"
            session = self._session(
                FakeResponse(headers={"content-length": "6"}),
                [FakeResponse(chunks=[b"abc", b"def"])],
            )
            worker = DownloadWorker(
                "download-1",
                "https://example.com/file.bin",
                target,
                segments=1,
                session=session,
            )
            completions = []
            worker.completed.connect(
                lambda download_id, success, message: completions.append(
                    (download_id, success, message)
                )
            )
            worker.run()
            self.assertEqual(target.read_bytes(), b"abcdef")
            self.assertEqual(
                completions,
                [("download-1", True, "Completed")],
            )

    def test_stream_rejects_truncated_content(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "short.bin"
            session = self._session(
                FakeResponse(headers={"content-length": "6"}),
                [FakeResponse(chunks=[b"abc"])],
            )
            worker = DownloadWorker(
                "short",
                "https://example.com/short.bin",
                target,
                segments=1,
                session=session,
            )
            completions = []
            worker.completed.connect(
                lambda *values: completions.append(values)
            )
            worker.run()
            self.assertFalse(target.exists())
            self.assertFalse(completions[0][1])
            self.assertIn("Size mismatch", completions[0][2])

    def test_segmented_download_rejects_server_ignoring_range(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "ignored.bin"
            session = self._session(
                FakeResponse(
                    headers={
                        "content-length": "4",
                        "accept-ranges": "bytes",
                    }
                ),
                [
                    FakeResponse(chunks=[b"abcd"], status_code=200),
                    FakeResponse(chunks=[b"abcd"], status_code=200),
                ],
            )
            worker = DownloadWorker(
                "ignored",
                "https://example.com/ignored.bin",
                target,
                segments=2,
                session=session,
            )
            completions = []
            worker.completed.connect(
                lambda *values: completions.append(values)
            )
            worker.run()
            self.assertFalse(target.exists())
            self.assertFalse(completions[0][1])
            self.assertIn("rejected byte range", completions[0][2])

    def test_segmented_download_validates_and_assembles_exact_ranges(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "parts.bin"
            session = self._session(
                FakeResponse(
                    headers={
                        "content-length": "6",
                        "accept-ranges": "bytes",
                    }
                ),
                [
                    FakeResponse(
                        chunks=[b"abc"],
                        headers={"content-range": "bytes 0-2/6"},
                        status_code=206,
                    ),
                    FakeResponse(
                        chunks=[b"def"],
                        headers={"content-range": "bytes 3-5/6"},
                        status_code=206,
                    ),
                ],
            )
            worker = DownloadWorker(
                "parts",
                "https://example.com/parts.bin",
                target,
                segments=2,
                session=session,
            )
            completions = []
            worker.completed.connect(
                lambda *values: completions.append(values)
            )
            worker.run()
            self.assertEqual(target.read_bytes(), b"abcdef")
            self.assertTrue(completions[0][1])

    def _relocating_worker(self, root, head, gets, url="https://e.com/download?id=7"):
        session = self._session(head, gets)
        worker = DownloadWorker(
            "r1", url, root / "Others" / "download", segments=1, session=session,
            router=lambda name: str(root / ("Programs/Mac" if name.endswith(".dmg") else "Others")),
        )
        moves, completions = [], []
        worker.relocated.connect(lambda *values: moves.append(values))
        worker.completed.connect(lambda *values: completions.append(values))
        return worker, moves, completions

    def test_content_disposition_routes_dmg_to_its_category(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            head = FakeResponse(headers={
                "content-length": "3",
                "content-disposition": 'attachment; filename="Windscribe.dmg"',
            })
            worker, moves, completions = self._relocating_worker(
                root, head, [FakeResponse(chunks=[b"dmg"])]
            )
            worker.run()
            target = root / "Programs" / "Mac" / "Windscribe.dmg"
            self.assertEqual(moves, [("r1", str(target))])
            self.assertEqual(target.read_bytes(), b"dmg")
            self.assertFalse((root / "Others" / "download").exists())
            self.assertTrue(completions[0][1])

    def test_redirect_url_name_is_used_when_head_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            session_head = Mock(side_effect=requests.ConnectionError("no HEAD"))
            worker, moves, _ = self._relocating_worker(
                root, None,
                [FakeResponse(chunks=[b"x"], url="https://cdn.e.com/v/App-1.2.dmg")],
            )
            worker.session.head = session_head
            worker.run()
            self.assertEqual(moves[0][1], str(root / "Programs" / "Mac" / "App-1.2.dmg"))

    def test_matching_name_is_not_relocated(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            worker, moves, _ = self._relocating_worker(
                root, FakeResponse(headers={"content-length": "1"}),
                [FakeResponse(chunks=[b"x"])], url="https://e.com/download",
            )
            worker.run()
            self.assertEqual(moves, [])


if __name__ == "__main__":
    unittest.main()
