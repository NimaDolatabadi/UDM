"""Tests for configuration persistence and category routing."""

import json
from pathlib import Path
import tempfile
import unittest

from udm.config import ConfigManager


class ConfigManagerTests(unittest.TestCase):
    def test_missing_config_is_created_with_independent_defaults(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "config.json"
            manager = ConfigManager(path, Path(temp) / "downloads")
            self.assertTrue(path.exists())
            self.assertEqual(manager.config["language"], "English")
            manager.config["language"] = "French"

            second_path = Path(temp) / "second.json"
            second = ConfigManager(second_path, Path(temp) / "other")
            self.assertEqual(second.config["language"], "English")

    def test_saved_values_merge_with_new_defaults(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "config.json"
            path.write_text(json.dumps({"language": "Italian"}), encoding="utf-8")
            manager = ConfigManager(path, Path(temp) / "downloads")
            self.assertEqual(manager.config["language"], "Italian")
            self.assertIn("segments", manager.config)
            self.assertEqual(manager.config["max_concurrent"], 4)
            self.assertIn("schedules", manager.config)

    def test_category_path_uses_configured_extension(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manager = ConfigManager(root / "config.json", root / "downloads")
            pdf_path = Path(manager.get_category_path("manual.PDF"))
            unknown_path = Path(manager.get_category_path("archive.unknown"))
            self.assertEqual(pdf_path, root / "downloads" / "Documents")
            self.assertEqual(unknown_path, root / "downloads" / "Others")
            self.assertTrue(pdf_path.is_dir())
            self.assertTrue(unknown_path.is_dir())


if __name__ == "__main__":
    unittest.main()
