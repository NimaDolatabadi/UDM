"""Tests for server filename detection and unique destination paths."""

from pathlib import Path
import tempfile
import unittest

from udm.filenames import (
    claim_unique_path,
    extension_for_type,
    from_content_disposition,
    remote_filename,
    sanitize,
    unique_path,
)


class FilenameTests(unittest.TestCase):
    def test_content_disposition_forms(self):
        self.assertEqual(
            from_content_disposition('attachment; filename="Windscribe 2.24.dmg"'),
            "Windscribe 2.24.dmg",
        )
        self.assertEqual(from_content_disposition("attachment; filename=app.pkg"), "app.pkg")
        self.assertEqual(
            from_content_disposition(
                "attachment; filename=\"fallback.dmg\"; filename*=UTF-8''%D9%81%D8%A7%DB%8C%D9%84.dmg"
            ),
            "فایل.dmg",
        )
        self.assertEqual(from_content_disposition("inline"), "")

    def test_names_cannot_escape_the_folder(self):
        self.assertEqual(from_content_disposition('attachment; filename="../../evil.sh"'), "_.._evil.sh")
        self.assertEqual(sanitize("..."), "")
        self.assertLessEqual(len(sanitize("a" * 300 + ".dmg")), 200)
        self.assertTrue(sanitize("a" * 300 + ".dmg").endswith(".dmg"))

    def test_remote_filename_priority(self):
        disposition = {"content-disposition": 'attachment; filename="real.dmg"'}
        self.assertEqual(remote_filename("https://e.com/x.zip", disposition, "download"), "real.dmg")
        self.assertEqual(
            remote_filename("https://cdn.e.com/files/App%201.0.dmg", {}, "download"), "App 1.0.dmg"
        )
        typed = {"content-type": "application/x-apple-diskimage"}
        self.assertEqual(remote_filename("https://e.com/get", typed, "get"), "get.dmg")
        generic = {"content-type": "application/octet-stream"}
        self.assertEqual(remote_filename("https://e.com/get", generic, "get"), "")

    def test_extension_for_common_download_types(self):
        self.assertEqual(extension_for_type("application/x-apple-diskimage"), ".dmg")
        self.assertEqual(extension_for_type("application/vnd.android.package-archive; x=1"), ".apk")
        self.assertEqual(extension_for_type("text/html"), "")

    def test_unique_and_claimed_paths(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "a.dmg").write_text("x")
            self.assertEqual(unique_path(root, "a.dmg"), root / "a (1).dmg")
            self.assertEqual(unique_path(root, "a.dmg", [root / "a (1).dmg"]), root / "a (2).dmg")
            first = claim_unique_path(root / "Programs" / "Mac", "b.dmg")
            second = claim_unique_path(root / "Programs" / "Mac", "b.dmg")
            self.assertEqual(first.name, "b.dmg")
            self.assertEqual(second.name, "b (1).dmg")
            self.assertTrue(first.exists() and second.exists())


if __name__ == "__main__":
    unittest.main()
