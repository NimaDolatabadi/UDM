"""Offscreen tests for dialogs and main-window composition."""

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from datetime import datetime

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QDateEdit, QTimeEdit

from udm.config import ConfigManager
from udm.ui.main_window import MainWindow
from udm.ui.options_dialog import OptionsDialog
from udm.ui.schedule_editor import ScheduleEditorDialog
from udm.ui.scheduler_dialog import SchedulerDialog


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


class SchedulerDialogTests(QtTestCase):
    def _schedule(self):
        return {
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

    def test_list_round_trips_records_and_live_enable_state(self):
        schedule = self._schedule()
        dialog = SchedulerDialog([schedule])
        # The list view holds no inline field editors; those live in the editor.
        self.assertEqual(len(dialog.findChildren(QDateEdit)), 0)
        dialog.schedule_rows[0]["active"].setChecked(False)
        updated = dialog.get_updated_schedules()[0]
        for field in (
            "start_date",
            "end_date",
            "start_time",
            "end_time",
            "recurrence",
        ):
            self.assertEqual(updated[field], schedule[field])
        self.assertFalse(updated["active"])
        dialog.close()

    def test_editor_exposes_date_and_time_fields_and_round_trips(self):
        schedule = self._schedule()
        editor = ScheduleEditorDialog(schedule)
        self.assertEqual(len(editor.findChildren(QDateEdit)), 2)
        self.assertEqual(len(editor.findChildren(QTimeEdit)), 2)
        values = editor.get_values()
        for field in (
            "start_date",
            "end_date",
            "start_time",
            "end_time",
            "recurrence",
        ):
            self.assertEqual(values[field], schedule[field])
        editor.close()

    def test_default_schedule_editor_hides_concurrency_and_blocks_delete(self):
        with tempfile.TemporaryDirectory() as temp:
            manager = ConfigManager(Path(temp) / "config.json")
            dialog = SchedulerDialog(manager.config["schedules"])
            self.assertTrue(dialog.schedule_rows[0]["is_default"])
            editor = ScheduleEditorDialog(manager.config["schedules"][0])
            self.assertTrue(editor.maximum.isHidden())
            editor.close()
            dialog.close()


class OptionsDialogTests(QtTestCase):
    def test_unedited_schedule_records_are_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            manager = ConfigManager(Path(temp) / "config.json")
            dialog = OptionsDialog(manager.config)
            updated = dialog.get_updated_config()
            self.assertEqual(updated["schedules"], manager.config["schedules"])
            dialog.close()

    def test_max_concurrent_downloads_is_editable_and_persisted(self):
        with tempfile.TemporaryDirectory() as temp:
            manager = ConfigManager(Path(temp) / "config.json")
            dialog = OptionsDialog(manager.config)
            self.assertEqual(dialog.max_concurrent.value(), 4)
            dialog.max_concurrent.setValue(7)
            self.assertEqual(dialog.get_updated_config()["max_concurrent"], 7)
            dialog.close()

    def test_theme_selection_defaults_and_round_trips(self):
        with tempfile.TemporaryDirectory() as temp:
            manager = ConfigManager(Path(temp) / "config.json")
            dialog = OptionsDialog(manager.config)
            self.assertEqual(dialog.theme.currentText(), "System")
            dialog.theme.setCurrentText("Light")
            self.assertEqual(dialog.get_updated_config()["theme"], "Light")
            dialog.close()

    def test_sidebar_navigation_switches_settings_pages(self):
        with tempfile.TemporaryDirectory() as temp:
            manager = ConfigManager(Path(temp) / "config.json")
            dialog = OptionsDialog(manager.config)
            self.assertEqual(dialog.pages.count(), 3)
            dialog.nav.setCurrentRow(2)
            self.assertEqual(dialog.pages.currentIndex(), 2)
            dialog.close()


class MainWindowTests(QtTestCase):
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

    def test_window_constructs_all_feature_tabs_and_actions(self):
        self.assertEqual(self.window.tabs.count(), 4)
        self.assertEqual(self.window.downloads_tab.table.columnCount(), 6)
        self.assertEqual(self.window.torrents_tab.table.columnCount(), 6)
        self.assertEqual(self.window.grabber_tab.results.columnCount(), 1)
        self.assertEqual(self.window.bulk_tab.results.columnCount(), 1)
        self.assertTrue(self.window.add_action.text())
        self.assertTrue(self.window.scheduler_action.text())

    def test_apply_theme_switches_stylesheet_and_tolerates_unknown_name(self):
        self.window.apply_theme("Light")
        self.assertEqual(self.window.current_theme.name, "Light")
        self.assertIn("#f6f7f9", self.application.styleSheet())
        self.window.apply_theme("Nonexistent Theme")
        self.assertEqual(self.window.current_theme.name, "Refined Dark")
        self.assertFalse(self.window.add_action.icon().isNull())

    def test_system_theme_resolves_to_a_concrete_theme(self):
        self.window.apply_theme("System")
        self.assertEqual(self.window.current_theme_option, "System")
        self.assertIn(self.window.current_theme.name, ("Refined Dark", "Light"))

    def test_window_reconciles_startup_preference_on_construction(self):
        with patch("udm.ui.main_window.sync_system_startup") as sync:
            window = MainWindow(config_manager=self.manager)
        sync.assert_called_once_with(False)
        window.close()

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

    def test_filename_collisions_get_unique_paths_and_labels(self):
        url = "https://example.com/files/archive.zip"
        self.window.add_to_downloads(url, start_paused=True)
        self.window.add_to_downloads(url, start_paused=True)
        table = self.window.downloads_tab.table
        self.assertEqual(table.item(0, 0).text(), "archive.zip")
        self.assertEqual(table.item(1, 0).text(), "archive (1).zip")

    def test_resume_ignores_completed_and_failed_rows(self):
        self.window.add_to_downloads(
            "https://example.com/files/archive.zip",
            start_paused=True,
        )
        table = self.window.downloads_tab.table
        for status in ("Completed", "Failed: network error"):
            table.setItem(0, 2, self._item(status))
            table.selectRow(0)
            with patch.object(self.window, "start_worker") as start:
                self.window.resume_selected()
                start.assert_not_called()

    def test_torrent_resume_does_not_change_placeholder_status(self):
        table = self.window.torrents_tab.table
        table.insertRow(0)
        name = self._item("sample.torrent")
        name.setData(Qt.ItemDataRole.UserRole, "torrent-1")
        table.setItem(0, 0, name)
        table.setItem(0, 2, self._item("Pending"))
        self.window.tabs.setCurrentWidget(self.window.torrents_tab)
        table.selectRow(0)
        self.window.resume_selected()
        self.assertEqual(table.item(0, 2).text(), "Pending")

    def test_delete_retains_running_worker_until_finished(self):
        self.window.add_to_downloads(
            "https://example.com/files/archive.zip",
            start_paused=True,
        )
        table = self.window.downloads_tab.table
        download_id = table.item(0, 0).data(Qt.ItemDataRole.UserRole)
        worker = FakeWorker()
        self.window.pending_downloads.pop(download_id)
        self.window.active_workers[download_id] = worker
        table.selectRow(0)
        self.window.delete_selected()
        self.assertTrue(worker.cancelled)
        self.assertIs(self.window.cancelling_workers[download_id], worker)
        self.window._worker_finished(download_id)
        self.assertNotIn(download_id, self.window.cancelling_workers)

    def test_default_queue_enforces_maximum_concurrency(self):
        self.manager.config["max_concurrent"] = 2
        for index in range(3):
            self.window.add_to_downloads(
                f"https://example.com/file-{index}.bin",
                start_paused=True,
            )
        self.window.manually_paused.clear()
        started = []

        def record_start(download_id, url, save_path):
            started.append(download_id)
            self.window.pending_downloads.pop(download_id)
            self.window.active_workers[download_id] = FakeWorker()

        with patch.object(self.window, "start_worker", side_effect=record_start):
            self.window.reconcile_download_queue()
        self.assertEqual(len(started), 2)
        self.assertEqual(len(self.window.pending_downloads), 1)

    def test_default_queue_ignores_default_schedule_maximum(self):
        self.manager.config["max_concurrent"] = 3
        self.manager.config["schedules"][0]["max_dl"] = 1
        for index in range(3):
            self.window.add_to_downloads(
                f"https://example.com/global-{index}.bin",
                start_paused=True,
            )
        self.window.manually_paused.clear()
        started = []

        def record_start(download_id, url, save_path):
            started.append(download_id)
            self.window.pending_downloads.pop(download_id)
            self.window.active_workers[download_id] = FakeWorker()

        with patch.object(self.window, "start_worker", side_effect=record_start):
            self.window.reconcile_download_queue()
        self.assertEqual(len(started), 3)

    def test_explicit_schedule_retains_its_own_concurrency_limit(self):
        self.manager.config["max_concurrent"] = 4
        self.manager.config["schedules"].append(
            {
                "name": "Night",
                "active": True,
                "max_dl": 1,
                "start_date": "2026-07-01",
                "end_date": "2026-07-31",
                "start_time": "22:00",
                "end_time": "23:00",
                "recurrence": "Every Day",
            }
        )
        for index in range(2):
            self.window.add_to_downloads(
                f"https://example.com/scheduled-{index}.bin",
                start_paused=True,
                schedule_idx=1,
            )
        self.window.manually_paused.clear()
        started = []

        def record_start(download_id, url, save_path):
            started.append(download_id)
            self.window.pending_downloads.pop(download_id)
            self.window.active_workers[download_id] = FakeWorker()

        with patch.object(self.window, "start_worker", side_effect=record_start):
            self.window.reconcile_download_queue(
                datetime(2026, 7, 10, 22, 30)
            )
        self.assertEqual(len(started), 1)

    def test_progress_populates_size_time_and_rate_columns(self):
        self.window.add_to_downloads(
            "https://example.com/files/archive.zip",
            start_paused=True,
        )
        table = self.window.downloads_tab.table
        download_id = table.item(0, 0).data(Qt.ItemDataRole.UserRole)
        self.window.manually_paused.discard(download_id)
        self.window.on_worker_progress(
            download_id,
            1024,
            4096,
            "2.0 KB/s",
            "00:00:01",
            "Downloading",
        )
        self.assertEqual(table.item(0, 1).text(), "1.0 KB / 4.0 KB")
        self.assertEqual(table.item(0, 3).text(), "00:00:01")
        self.assertEqual(table.item(0, 4).text(), "2.0 KB/s")

    def test_paused_status_ignores_stale_worker_progress(self):
        self.window.add_to_downloads(
            "https://example.com/files/archive.zip",
            start_paused=True,
        )
        table = self.window.downloads_tab.table
        download_id = table.item(0, 0).data(Qt.ItemDataRole.UserRole)
        self.window.on_worker_progress(
            download_id,
            1024,
            4096,
            "2.0 KB/s",
            "00:00:01",
            "Downloading",
        )
        self.assertEqual(table.item(0, 2).text(), "Paused")

    def test_explicit_schedule_starts_and_restores_status_inside_window(self):
        self.manager.config["schedules"].append(
            {
                "name": "Night",
                "active": True,
                "max_dl": 1,
                "start_date": "2026-07-01",
                "end_date": "2026-07-31",
                "start_time": "22:00",
                "end_time": "23:00",
                "recurrence": "Every Day",
            }
        )
        self.window.add_to_downloads(
            "https://example.com/night.bin",
            start_paused=True,
            schedule_idx=1,
        )
        self.window.manually_paused.clear()
        started = []

        def record_start(download_id, url, save_path):
            started.append(download_id)
            self.window.pending_downloads.pop(download_id)
            self.window.active_workers[download_id] = FakeWorker()

        with patch.object(self.window, "start_worker", side_effect=record_start):
            self.window.reconcile_download_queue(
                datetime(2026, 7, 10, 12, 0)
            )
            self.assertFalse(started)
            self.window.reconcile_download_queue(
                datetime(2026, 7, 10, 22, 30)
            )
            self.window.reconcile_download_queue(
                datetime(2026, 7, 11, 12, 0)
            )
            self.assertEqual(
                self.window.downloads_tab.table.item(0, 2).text(),
                "Scheduled",
            )
            self.window.reconcile_download_queue(
                datetime(2026, 7, 11, 22, 30)
            )
        self.assertEqual(len(started), 1)
        self.assertEqual(
            self.window.downloads_tab.table.item(0, 2).text(),
            "Downloading",
        )
        self.assertFalse(self.window.active_workers[started[0]].paused)

    @staticmethod
    def _item(text):
        from PyQt6.QtWidgets import QTableWidgetItem

        return QTableWidgetItem(text)


if __name__ == "__main__":
    unittest.main()
