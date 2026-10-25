"""Tests for yt-dlp option building and the stream worker lifecycle."""

from pathlib import Path
import tempfile
import unittest

from udm.workers.stream import StreamWorker
from udm.workers.ytdlp_options import build_options, format_for_quality


class FakeDownloader:
    """Stand in for YoutubeDL, replaying scripted progress hook calls."""

    def __init__(self, options, statuses, error=None):
        from http.cookiejar import CookieJar

        self.cookiejar = CookieJar()
        self.options = options
        self.statuses = statuses
        self.error = error
        self.urls = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def download(self, urls):
        self.urls.extend(urls)
        for status in self.statuses:
            for hook in self.options["progress_hooks"]:
                hook(status)
        if self.error:
            raise self.error
        return 0


class OptionTests(unittest.TestCase):
    def test_options_carry_headers_quality_proxy_and_ffmpeg(self):
        options = build_options(
            "/downloads/Videos",
            headers={"Referer": "https://site.example/"},
            quality="720p",
            proxy="http://proxy:8080",
            fragments=64,
            ffmpeg="/bin/ffmpeg",
            deno="/bin/deno",
        )
        self.assertEqual(options["format"], format_for_quality("720p"))
        self.assertEqual(options["js_runtimes"], {"deno": {"path": "/bin/deno"}})
        self.assertEqual(options["format_sort"][1], "vcodec:h264")
        self.assertEqual(options["http_headers"], {"Referer": "https://site.example/"})
        self.assertEqual(options["proxy"], "http://proxy:8080")
        self.assertEqual(options["ffmpeg_location"], "/bin/ffmpeg")
        self.assertEqual(options["concurrent_fragment_downloads"], 16)
        self.assertEqual(options["merge_output_format"], "mp4")
        self.assertTrue(options["outtmpl"]["default"].startswith("/downloads/Videos/"))
        self.assertTrue(options["noplaylist"])

    def test_audio_only_skips_merge_and_unknown_quality_uses_best(self):
        self.assertNotIn(
            "merge_output_format", build_options("/d", quality="Audio Only", ffmpeg="", deno="")
        )
        self.assertNotIn("merge_output_format", build_options("/d", quality="audio", ffmpeg="", deno=""))
        self.assertNotIn("js_runtimes", build_options("/d", ffmpeg="", deno=""))
        self.assertEqual(format_for_quality("8K"), format_for_quality("Best"))

    def test_any_height_maps_to_a_height_limited_selector(self):
        self.assertEqual(format_for_quality("1440p"), "bv*[height<=1440]+ba/b[height<=1440]/b")
        self.assertEqual(format_for_quality("best"), "bv*+ba/b")


class StreamWorkerTests(unittest.TestCase):
    def _worker(self, target, statuses, error=None):
        holder = {}

        def factory(options):
            holder["downloader"] = FakeDownloader(options, statuses, error)
            return holder["downloader"]

        worker = StreamWorker(
            "s1", "https://site.example/watch", target,
            headers={"Referer": "https://site.example/"}, downloader_factory=factory,
            cookie_jar=({"name": "sid", "value": "9", "domain": ".site.example",
                         "path": "/", "secure": True, "hostOnly": False},),
        )
        events = {"progress": [], "completed": [], "renamed": []}
        worker.progress.connect(lambda *v: events["progress"].append(v))
        worker.completed.connect(lambda *v: events["completed"].append(v))
        worker.renamed.connect(lambda *v: events["renamed"].append(v))
        return worker, events, holder

    def test_progress_title_and_completion_are_reported(self):
        statuses = [
            {"status": "downloading", "downloaded_bytes": 512, "total_bytes_estimate": 2048,
             "speed": 1024, "eta": 2, "info_dict": {"title": "My Clip"}},
            {"status": "finished", "filename": "x.mp4", "info_dict": {"title": "My Clip"}},
        ]
        with tempfile.TemporaryDirectory() as temp:
            worker, events, holder = self._worker(temp, statuses)
            worker.run()
        self.assertEqual(holder["downloader"].urls, ["https://site.example/watch"])
        self.assertEqual(
            holder["downloader"].options["http_headers"], {"Referer": "https://site.example/"}
        )
        cookies = list(holder["downloader"].cookiejar)
        self.assertEqual([(c.name, c.domain) for c in cookies], [("sid", ".site.example")])
        self.assertEqual(events["renamed"], [("s1", "My Clip")])
        self.assertEqual(events["progress"][0], ("s1", 512, 2048, "1.0 KB/s", "00:00:02", "Downloading"))
        self.assertEqual(events["completed"], [("s1", True, "Completed")])

    def test_failure_reports_first_error_line(self):
        with tempfile.TemporaryDirectory() as temp:
            worker, events, _ = self._worker(temp, [], RuntimeError("ERROR: Unsupported URL\nmore"))
            worker.run()
        self.assertEqual(events["completed"], [("s1", False, "Unsupported URL")])

    def test_cancel_removes_partials_without_reporting(self):
        with tempfile.TemporaryDirectory() as temp:
            partial = Path(temp) / "clip.mp4.part"
            fragment = Path(temp) / "clip.mp4.part-Frag3.part"
            keep = Path(temp) / "other.mp4"
            for path in (partial, fragment, keep):
                path.write_bytes(b"data")
            statuses = [{"status": "downloading", "tmpfilename": str(partial)}] * 2
            worker, events, _ = self._worker(temp, statuses)
            original = worker._remember_partial

            def remember_then_cancel(status):
                original(status)
                worker.cancel()

            worker._remember_partial = remember_then_cancel
            worker.run()
            self.assertFalse(partial.exists())
            self.assertFalse(fragment.exists())
            self.assertTrue(keep.exists())
        self.assertEqual(events["completed"], [])


if __name__ == "__main__":
    unittest.main()
