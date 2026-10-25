"""Application lifecycle smoke test."""

import os
from pathlib import Path
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QTimer

from udm.app import create_application
from udm.config import ConfigManager


class ApplicationSmokeTests(unittest.TestCase):
    def test_application_enters_and_exits_event_loop_cleanly(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manager = ConfigManager(root / "config.json", root / "downloads")
            manager.config["close_to_tray"] = False
            application, window = create_application(
                [],
                config_manager=manager,
                sync_startup=False,
            )
            window.show()
            QTimer.singleShot(50, window.close)
            QTimer.singleShot(100, application.quit)
            exit_code = application.exec()
            self.assertEqual(exit_code, 0)
            self.assertFalse(window.isVisible())


if __name__ == "__main__":
    unittest.main()
