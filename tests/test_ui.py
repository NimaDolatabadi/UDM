"""Offscreen tests for dialogs and main-window composition."""

import os
from pathlib import Path
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QDateEdit, QTimeEdit

from udm.config import ConfigManager
from udm.ui.main_window import MainWindow
from udm.ui.options_dialog import OptionsDialog
from udm.ui.scheduler_dialog import SchedulerDialog


class QtTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])


class SchedulerDialogTests(QtTestCase):
    def test_schedule_round_trip_preserves_date_and_time_fields(self):
        schedule = {
            "name": "Night",
            "active": True,
            "max_dl": 3,
            "start_date": "2026-07-01",
            "end_date": "2026-07-31",
            "start_time": "01:30",
            "end_time": "05:45",
            "recurrence": "Odd Days",
            "color": "#3399ff",
            "is_default": False,
        }
        dialog = SchedulerDialog([schedule])
        self.assertEqual(len(dialog.findChildren(QDateEdit)), 2)
        self.assertEqual(len(dialog.findChildren(QTimeEdit)), 2)
        updated = dialog.get_updated_schedules()[0]
        for field in (
            "start_date",
            "end_date",
            "start_time",
            "end_time",
            "recurrence",
        ):
            self.assertEqual(updated[field], schedule[field])
        dialog.close()


class OptionsDialogTests(QtTestCase):
    def test_unedited_schedule_records_are_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            manager = ConfigManager(Path(temp) / "config.json")
            dialog = OptionsDialog(manager.config)
            updated = dialog.get_updated_config()
            self.assertEqual(updated["schedules"], manager.config["schedules"])
            dialog.close()


class MainWindowTests(QtTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.manager = ConfigManager(root / "config.json", root / "downloads")
        self.manager.config["close_to_tray"] = False
        self.window = MainWindow(
            config_manager=self.manager,
            register_startup=False,
        )

    def tearDown(self):
        self.window.close()
        self.application.processEvents()
        self.temp.cleanup()

    def test_window_constructs_all_feature_tabs_and_actions(self):
        self.assertEqual(self.window.tabs.count(), 4)
        self.assertEqual(self.window.downloads_tab.table.columnCount(), 6)
        self.assertEqual(self.window.torrents_tab.table.columnCount(), 6)
        self.assertEqual(self.window.grabber_tab.results.columnCount(), 1)
        self.assertEqual(self.window.bulk_tab.results.columnCount(), 1)
        self.assertTrue(self.window.add_action.text())
        self.assertTrue(self.window.scheduler_action.text())

    def test_paused_download_can_be_added_without_network_access(self):
        self.window.add_to_downloads(
            "https://example.com/files/archive.zip",
            start_paused=True,
        )
        table = self.window.downloads_tab.table
        self.assertEqual(table.rowCount(), 1)
        self.assertEqual(table.item(0, 0).text(), "archive.zip")
        self.assertEqual(table.item(0, 2).text(), "Paused")

    def test_translation_updates_tab_and_action_labels(self):
        self.manager.config["language"] = "French"
        self.window.retranslate_ui()
        self.assertEqual(
            self.window.tabs.tabText(self.window.tabs.indexOf(self.window.downloads_tab)),
            "Téléchargements",
        )
        self.assertEqual(self.window.add_action.text(), "Ajouter URL")


if __name__ == "__main__":
    unittest.main()
