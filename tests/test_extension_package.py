"""Tests for the standalone extension release files and the self-check."""

import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from udm import self_check
from udm.bridge import extension_build, extension_package
from udm.bridge.browsers import CHROMIUM, FIREFOX


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_release_files_are_named_per_engine(self):
        written = extension_package.package_all(self.root / "dist", "1.2.3")
        self.assertEqual([path.name for path in written], [
            "udm-capture-chromium-1.2.3.zip", "udm-capture-firefox-1.2.3.xpi",
        ])

    def test_archives_match_the_apps_build(self):
        for engine in (CHROMIUM, FIREFOX):
            archive = extension_package.package(engine, self.root / "dist", "1.2.3")
            built = extension_build.build_extension(
                engine, self.root / "built" / engine, "1.2.3"
            )
            expected = {
                path.relative_to(built).as_posix(): path.read_bytes()
                for path in built.rglob("*") if path.is_file()
            }
            with zipfile.ZipFile(archive) as opened:
                contents = {name: opened.read(name) for name in opened.namelist()}
            self.assertEqual(contents, expected)
            self.assertEqual(json.loads(contents["manifest.json"])["version"], "1.2.3")

    def test_archives_are_reproducible(self):
        first = extension_package.package(FIREFOX, self.root / "a", "1.0.0").read_bytes()
        second = extension_package.package(FIREFOX, self.root / "b", "1.0.0").read_bytes()
        self.assertEqual(first, second)

    def test_main_prints_each_path(self):
        with patch("sys.stdout", new_callable=io.StringIO) as out:
            self.assertEqual(extension_package.main([str(self.root / "dist")]), 0)
        self.assertEqual(len(out.getvalue().splitlines()), 2)


class SelfCheckTests(unittest.TestCase):
    def test_source_checkout_passes(self):
        stream = io.StringIO()
        self.assertEqual(self_check.run(stream), 0)
        self.assertIn("self-check passed", stream.getvalue())

    def test_import_failures_and_missing_modules_are_reported(self):
        def importer(name):
            raise ImportError("missing dependency")

        failures = self_check.check_imports(["udm.app"], importer)
        names = [name for name, _ in failures]
        self.assertIn("module list", names)
        self.assertIn("udm.app", names)


if __name__ == "__main__":
    unittest.main()
