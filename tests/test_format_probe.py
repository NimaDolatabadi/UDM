"""Tests for quality listing and yt-dlp cookie loading."""

from http.cookiejar import CookieJar
import unittest

from udm.capture import CaptureRequest
from udm.workers.format_probe import probe_qualities, qualities_from_formats
from udm.workers.ytdlp_cookies import load_cookies

MB = 1024 * 1024
FORMATS = [
    {"format_id": "a1", "vcodec": "none", "acodec": "opus", "abr": 50, "ext": "webm", "filesize": 2 * MB},
    {"format_id": "a2", "vcodec": "none", "acodec": "mp4a", "abr": 128, "ext": "m4a", "filesize": 4 * MB},
    {"format_id": "v720", "vcodec": "avc1", "acodec": "none", "height": 720, "tbr": 1500, "filesize": 40 * MB},
    {"format_id": "v720b", "vcodec": "vp9", "acodec": "none", "height": 720, "tbr": 900, "filesize": 30 * MB},
    {"format_id": "v1080", "vcodec": "avc1", "acodec": "none", "height": 1080, "tbr": 3000, "filesize_approx": 90 * MB},
    {"format_id": "p360", "vcodec": "avc1", "acodec": "mp4a", "height": 360, "tbr": 600},
]


class FakeYoutubeDL:
    def __init__(self, options, info=None, error=None):
        self.options = options
        self.info = info
        self.error = error
        self.cookiejar = CookieJar()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def extract_info(self, url, download=True):
        if self.error:
            raise self.error
        return self.info


class QualityTests(unittest.TestCase):
    def test_qualities_are_ordered_with_merged_sizes(self):
        choices = qualities_from_formats(FORMATS)
        self.assertEqual([c["quality"] for c in choices], ["best", "1080p", "720p", "360p", "audio"])
        self.assertEqual(choices[1]["detail"], "MP4 - about 94 MB")
        self.assertEqual(choices[2]["detail"], "MP4 - about 44 MB")
        self.assertEqual(choices[3]["detail"], "MP4")
        estimated = qualities_from_formats(FORMATS, duration=100)
        # 600 kbit/s for 100 s is 7.5 MB.
        self.assertEqual(estimated[3]["detail"], "MP4 - about 7 MB")
        self.assertEqual(choices[4]["detail"], "M4A - about 4 MB")

    def test_probe_returns_title_qualities_and_loads_cookies(self):
        holder = {}

        def factory(options):
            holder["ydl"] = FakeYoutubeDL(options, {"title": "Clip", "formats": FORMATS})
            return holder["ydl"]

        request = CaptureRequest.from_message({
            "type": "formats", "url": "https://v.example/w", "cookies": "sid=1", "userAgent": "UA",
        })
        reply = probe_qualities(request, downloader_factory=factory)
        self.assertTrue(reply["ok"])
        self.assertEqual(reply["title"], "Clip")
        self.assertTrue(holder["ydl"].options["skip_download"])
        self.assertEqual(holder["ydl"].options["http_headers"], {"User-Agent": "UA"})
        self.assertEqual([c.name for c in holder["ydl"].cookiejar], ["sid"])

    def test_probe_failure_is_reported(self):
        request = CaptureRequest.from_message({"type": "formats", "url": "https://v.example/w"})
        reply = probe_qualities(
            request,
            downloader_factory=lambda o: FakeYoutubeDL(o, error=RuntimeError("ERROR: Private video")),
        )
        self.assertEqual(reply, {"ok": False, "error": "Private video"})


class CookieTests(unittest.TestCase):
    def test_records_keep_scope_and_header_falls_back_to_host(self):
        jar = CookieJar()
        added = load_cookies(jar, "https://www.v.example/w", (
            {"name": "a", "value": "1", "domain": "v.example", "path": "/", "hostOnly": False},
            {"name": "b", "value": "2", "domain": "www.v.example", "path": "/x", "hostOnly": True},
        ))
        self.assertEqual(added, 2)
        scopes = sorted((c.name, c.domain, c.path) for c in jar)
        self.assertEqual(scopes, [("a", ".v.example", "/"), ("b", "www.v.example", "/x")])
        header_jar = CookieJar()
        self.assertEqual(load_cookies(header_jar, "https://v.example/", (), "x=1; y=2"), 2)
        self.assertEqual({c.domain for c in header_jar}, {"v.example"})


if __name__ == "__main__":
    unittest.main()
