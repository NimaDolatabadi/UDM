"""Shared Qt fixtures for offscreen UI tests."""

import os
from pathlib import Path
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QTableWidgetItem

from udm.config import ConfigManager
from udm.ui.main_window import MainWindow


class FakeSignal:
    def __init__(self):
        self.callbacks = []

    def connect(self, callback):
        self.callbacks.append(callback)


class FakeWorker:
    def __init__(self):
        self.cancelled = False
        self.paused = False
        self.finished = FakeSignal()

    def cancel(self):
        self.cancelled = True

    def pause(self):
        self.paused = True

    def resume(self):
        self.paused = False

    def wait(self, timeout):
        return True


class QtTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])


class MainWindowTestCase(QtTestCase):
    """Construct an isolated main window around a temporary configuration."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.manager = ConfigManager(root / "config.json", root / "downloads")
        self.manager.config["close_to_tray"] = False
        self.window = MainWindow(
            config_manager=self.manager,
            sync_startup=False,
        )

    def tearDown(self):
        self.window.close()
        self.application.processEvents()
        self.temp.cleanup()


    @staticmethod
    def _item(text):
        return QTableWidgetItem(text)

    def _recording_starter(self, started):
        """Return a start_worker replacement that records admitted downloads."""

        def record_start(download_id, url, save_path):
            started.append(download_id)
            self.window.pending_downloads.pop(download_id)
            self.window.active_workers[download_id] = FakeWorker()

        return record_start
