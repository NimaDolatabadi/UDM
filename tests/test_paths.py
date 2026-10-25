"""Tests for data locations, legacy migration, and launch commands."""

import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import udm
from udm import paths


class PathsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        patcher = patch.dict(os.environ, {"UDM_DATA_DIR": str(self.root / "data")})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.temp.cleanup)

    def test_data_dir_override_is_created(self):
        self.assertEqual(paths.data_dir(), self.root / "data")
        self.assertTrue((self.root / "data").is_dir())
        self.assertEqual(paths.bridge_socket_path().parent, self.root / "data")

    def test_long_data_dir_uses_short_socket_path(self):
        long_dir = self.root / ("d" * 120)
        with patch.dict(os.environ, {"UDM_DATA_DIR": str(long_dir)}):
            socket_path = paths.bridge_socket_path()
            self.assertEqual(socket_path, paths.bridge_socket_path())
        self.assertLessEqual(len(os.fsencode(socket_path)), 100)
        self.assertNotEqual(socket_path.parent, long_dir)

    def test_legacy_config_is_copied_once(self):
        legacy_dir = self.root / "legacy"
        legacy_dir.mkdir()
        (legacy_dir / "udm_config.json").write_text('{"language": "French"}')
        target = paths.resolve_config_path(legacy_dir)
        self.assertEqual(target.read_text(), '{"language": "French"}')
        (legacy_dir / "udm_config.json").write_text('{"language": "Italian"}')
        paths.resolve_config_path(legacy_dir)
        self.assertEqual(target.read_text(), '{"language": "French"}')

    def test_source_command_runs_entry_script(self):
        command = paths.app_command()
        self.assertEqual(command[0], sys.executable)
        self.assertTrue(command[1].endswith("MACDM.py"))
        self.assertIsNone(paths.app_bundle())

    def test_frozen_command_is_the_bundle_executable(self):
        executable = "/Applications/UDM.app/Contents/MacOS/UDM"
        with patch.object(sys, "frozen", True, create=True), patch.object(
            sys, "executable", executable
        ):
            self.assertEqual(paths.app_command(), [executable])
            self.assertEqual(paths.app_bundle(), Path("/Applications/UDM.app"))

    def test_package_version_matches_version_file(self):
        version = (Path(__file__).resolve().parents[1] / "VERSION").read_text()
        self.assertEqual(udm.__version__, version.strip())


if __name__ == "__main__":
    unittest.main()
