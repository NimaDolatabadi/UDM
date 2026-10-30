"""Offscreen tests for dialogs and main-window composition."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PyQt6.QtWidgets import QDateEdit, QTimeEdit

from tests.qt_support import MainWindowTestCase, QtTestCase
from udm.config import ConfigManager
from udm.ui.main_window import MainWindow
from udm.ui.options_dialog import OptionsDialog
from udm.ui.schedule_editor import ScheduleEditorDialog
from udm.ui.scheduler_dialog import SchedulerDialog


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
            self.assertEqual(dialog.downloads_page.max_concurrent.value(), 4)
            dialog.downloads_page.max_concurrent.setValue(7)
            self.assertEqual(dialog.get_updated_config()["max_concurrent"], 7)
            dialog.close()

    def test_download_folder_round_trips_and_defaults_to_empty(self):
        with tempfile.TemporaryDirectory() as temp:
            manager = ConfigManager(Path(temp) / "config.json")
            dialog = OptionsDialog(manager.config)
            self.assertEqual(dialog.get_updated_config()["download_dir"], "")
            dialog.downloads_page.download_dir.setText(" /Volumes/Data/Downloads ")
            self.assertEqual(
                dialog.get_updated_config()["download_dir"], "/Volumes/Data/Downloads"
            )
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
            self.assertEqual(dialog.pages.count(), 5)
            self.assertEqual(dialog.nav.item(1).text(), "Downloads")
            dialog.nav.setCurrentRow(2)
            self.assertEqual(dialog.pages.currentIndex(), 2)
            dialog.close()


class MainWindowTests(MainWindowTestCase):
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


if __name__ == "__main__":
    unittest.main()
