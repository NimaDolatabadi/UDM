"""Tests for validation of browser capture requests."""

import unittest

from udm.capture import FILE_KIND, STREAM_KIND, CaptureRequest


class CaptureRequestTests(unittest.TestCase):
    def test_download_message_builds_file_request_with_session_headers(self):
        request = CaptureRequest.from_message(
            {
                "type": "download",
                "url": " https://example.com/a.zip ",
                "referrer": "https://example.com/page",
                "cookies": "sid=1; theme=dark",
                "userAgent": "Agent/1.0",
                "filename": "a.zip",
            }
        )
        self.assertEqual(request.kind, FILE_KIND)
        self.assertEqual(request.url, "https://example.com/a.zip")
        self.assertEqual(
            request.headers(),
            {
                "User-Agent": "Agent/1.0",
                "Referer": "https://example.com/page",
                "Cookie": "sid=1; theme=dark",
            },
        )

    def test_stream_message_uses_title_as_display_name(self):
        request = CaptureRequest.from_message(
            {"type": "stream", "url": "https://video.example/watch?v=1", "title": "Clip"}
        )
        self.assertEqual(request.kind, STREAM_KIND)
        self.assertEqual(request.display_name(), "Clip")
        self.assertEqual(request.headers(), {})

    def test_rejects_unknown_type_non_http_url_and_header_injection(self):
        invalid = (
            {"type": "launch", "url": "https://example.com"},
            {"type": "download", "url": "file:///etc/passwd"},
            {"type": "download", "url": "blob:https://example.com/1"},
            {"type": "download", "url": "https://e.com", "cookies": "a=1\r\nX: y"},
            {"type": "download", "url": "https://e.com", "referrer": 5},
            "not a dict",
        )
        for message in invalid:
            with self.assertRaises(ValueError, msg=message):
                CaptureRequest.from_message(message)

    def test_quality_and_cookie_records_are_validated(self):
        request = CaptureRequest.from_message({
            "type": "stream", "url": "https://v.example/w", "quality": "720P",
            "cookies": "a=1", "userAgent": "UA",
            "cookieJar": [{"name": "a", "value": "1", "domain": ".v.example", "path": "/",
                           "secure": 1, "hostOnly": False, "expirationDate": 1.5e9}],
        })
        self.assertEqual(request.quality, "720p")
        self.assertEqual(request.cookie_jar[0]["secure"], True)
        self.assertEqual(request.stream_headers(), {"User-Agent": "UA"})
        self.assertIn("Cookie", request.headers())
        for bad in (
            {"quality": "best; rm"},
            {"cookieJar": "a=1"},
            {"cookieJar": [{"name": 5}]},
            {"cookieJar": [{}] * 501},
        ):
            with self.assertRaises(ValueError, msg=bad):
                CaptureRequest.from_message({"type": "stream", "url": "https://v.example", **bad})

    def test_formats_message_resolves_like_a_stream(self):
        request = CaptureRequest.from_message({"type": "formats", "url": "https://v.example/w"})
        self.assertEqual(request.kind, STREAM_KIND)


if __name__ == "__main__":
    unittest.main()
