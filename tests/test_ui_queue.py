"""Offscreen tests for download queue actions, admission, and progress."""

from datetime import datetime
import unittest
from unittest.mock import patch

from PyQt6.QtCore import Qt

from tests.qt_support import FakeWorker, MainWindowTestCase
from udm.ui.download_roles import PATH_ROLE


class QueueTests(MainWindowTestCase):
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

    def test_relocation_updates_row_name_path_and_folder(self):
        self.window.add_to_downloads("https://e.com/download?id=7", start_paused=True)
        table = self.window.downloads_tab.table
        download_id = table.item(0, 0).data(Qt.ItemDataRole.UserRole)
        self.assertIn("Others", table.item(0, 5).text())
        target = "/Users/x/Downloads/Programs/Mac/App.dmg"
        self.window.on_worker_relocated(download_id, target)
        self.assertEqual(table.item(0, 0).text(), "App.dmg")
        self.assertEqual(table.item(0, 0).data(PATH_ROLE), target)
        self.assertEqual(table.item(0, 5).text(), "Saved to: /Users/x/Downloads/Programs/Mac")


if __name__ == "__main__":
    unittest.main()
