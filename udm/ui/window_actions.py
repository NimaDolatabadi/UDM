"""Toolbar, localization, and settings actions for the main window."""

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QDialog,
    QMessageBox,
    QToolBar,
)

from udm.constants import DEFAULT_CONFIG
from udm.i18n import TRANSLATIONS
from udm.startup import set_system_startup
from udm.ui.options_dialog import OptionsDialog
from udm.ui.scheduler_dialog import SchedulerDialog
from udm.ui.theme import ACTION_GLYPHS, DEFAULT_THEME, TAB_GLYPHS, render_glyph


class WindowActions:
    """Build actions and coordinate application-level dialogs."""

    def create_toolbar(self):
        """Create shared queue, scheduler, settings, and navigation actions."""
        self.toolbar = QToolBar("Main Toolbar")
        self.toolbar.setIconSize(QSize(22, 22))
        self.toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        self.addToolBar(self.toolbar)
        self.add_action = QAction("", self)
        self.resume_action = QAction("", self)
        self.stop_action = QAction("", self)
        self.stop_all_action = QAction("", self)
        self.delete_action = QAction("", self)
        self.delete_completed_action = QAction("", self)
        self.scheduler_action = QAction("", self)
        self.options_action = QAction("", self)
        self.grabber_action = QAction("", self)
        # Map each action to its glyph key so icons can be re-tinted on a theme
        # change without rebuilding the toolbar.
        self._action_glyphs = {
            self.add_action: "add_url",
            self.resume_action: "resume",
            self.stop_action: "stop",
            self.stop_all_action: "stop_all",
            self.delete_action: "delete",
            self.delete_completed_action: "del_comp",
            self.scheduler_action: "scheduler",
            self.options_action: "options",
            self.grabber_action: "grabber",
        }
        self.toolbar.addActions(
            [
                self.add_action,
                self.resume_action,
                self.stop_action,
                self.stop_all_action,
                self.delete_action,
                self.delete_completed_action,
            ]
        )
        self.toolbar.addSeparator()
        self.toolbar.addActions(
            [
                self.scheduler_action,
                self.options_action,
                self.grabber_action,
            ]
        )
        self.add_action.triggered.connect(self.prompt_add_url)
        self.resume_action.triggered.connect(self.resume_selected)
        self.stop_action.triggered.connect(self.pause_selected)
        self.stop_all_action.triggered.connect(self.stop_all)
        self.delete_action.triggered.connect(self.delete_selected)
        self.delete_completed_action.triggered.connect(self.delete_completed)
        self.scheduler_action.triggered.connect(self.show_scheduler)
        self.options_action.triggered.connect(self.show_options)
        self.grabber_action.triggered.connect(
            lambda: self.tabs.setCurrentWidget(self.grabber_tab)
        )
        self.refresh_action_icons()

    def refresh_action_icons(self):
        """Re-render toolbar, tab, and queue icons for the active theme."""
        theme = self.current_theme
        color = theme.text_primary
        for action, key in self._action_glyphs.items():
            action.setIcon(render_glyph(ACTION_GLYPHS[key], color))
        for tab, key in (
            (self.downloads_tab, "downloads"),
            (self.torrents_tab, "torrents"),
            (self.grabber_tab, "grabber"),
            (self.bulk_tab, "bulk"),
        ):
            self.tabs.setTabIcon(
                self.tabs.indexOf(tab),
                render_glyph(TAB_GLYPHS[key], color, size=16),
            )
        # Queue-tree glyphs keep their color meaning: accent for the download
        # queue, success green for the sync queue.
        self.main_queue.setIcon(
            0, render_glyph("queue", theme.accent, size=18)
        )
        self.sync_queue.setIcon(
            0, render_glyph("sync", theme.status_success, size=18)
        )

    def retranslate_ui(self):
        """Apply the configured language to every translatable window widget."""
        language = self.config_manager.config.get("language", "English")
        text = TRANSLATIONS.get(language, TRANSLATIONS["English"])
        self.setWindowTitle(text["title"])
        action_labels = (
            (self.add_action, "add_url"),
            (self.resume_action, "resume"),
            (self.stop_action, "stop"),
            (self.stop_all_action, "stop_all"),
            (self.delete_action, "delete"),
            (self.delete_completed_action, "del_comp"),
            (self.scheduler_action, "scheduler"),
            (self.options_action, "options"),
            (self.grabber_action, "grabber"),
        )
        for action, key in action_labels:
            action.setText(text[key])
        self.queue_root.setText(0, text["q_queues"])
        self.main_queue.setText(0, text["q_main"])
        self.sync_queue.setText(0, text["q_sync"])
        for tab, key in (
            (self.downloads_tab, "tab_dl"),
            (self.torrents_tab, "tab_torrents"),
            (self.grabber_tab, "tab_grabber"),
            (self.bulk_tab, "tab_bulk"),
        ):
            self.tabs.setTabText(self.tabs.indexOf(tab), text[key])
        self.downloads_tab.table.setHorizontalHeaderLabels(text["dl_headers"])
        self.torrents_tab.table.setHorizontalHeaderLabels(text["tor_headers"])
        self.grabber_tab.results.setHorizontalHeaderLabels(text["grab_headers"])
        self.torrents_tab.add_magnet_button.setText(text["btn_add_mag"])
        self.torrents_tab.load_torrent_button.setText(text["btn_load_tor"])
        self.torrents_tab.magnet_input.setPlaceholderText(text["mag_ph"])
        self.grabber_tab.start_button.setText(text["btn_spider"])
        self.grabber_tab.url_input.setPlaceholderText(text["url_ph"])
        self.grabber_tab.filter_input.setPlaceholderText(text["filter_ph"])
        self.grabber_tab.select_all_button.setText(text["btn_sel_all"])
        self.grabber_tab.transfer_button.setText(text["btn_trans"])
        direction = (
            Qt.LayoutDirection.RightToLeft
            if language == "Persian"
            else Qt.LayoutDirection.LeftToRight
        )
        self.setLayoutDirection(direction)

    def show_scheduler(self):
        """Open the scheduler and persist accepted schedule records."""
        schedules = self.config_manager.config.get(
            "schedules",
            DEFAULT_CONFIG["schedules"],
        )
        dialog = SchedulerDialog(schedules, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.config_manager.config["schedules"] = (
                dialog.get_updated_schedules()
            )
            self.config_manager.save_config(self.config_manager.config)
            self.reconcile_download_queue()
            QMessageBox.information(
                self,
                "Scheduler Updated",
                "Schedules saved successfully.",
            )

    def show_options(self):
        """Open application settings and apply accepted changes."""
        dialog = OptionsDialog(self.config_manager.config, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        old_startup = self.config_manager.config.get("start_with_os", False)
        new_config = dialog.get_updated_config()
        self.config_manager.save_config(new_config)
        new_startup = new_config.get("start_with_os", False)
        # Startup registration touches platform state, so avoid rewriting it
        # when the user changed an unrelated option.
        if new_startup != old_startup:
            set_system_startup(new_startup)
        if self.tray_icon:
            self.tray_icon.setVisible(new_config.get("close_to_tray", True))
        if new_config.get("clipboard_monitor", False):
            self.setup_clipboard_monitor()
        else:
            self.teardown_clipboard_monitor()
        self.retranslate_ui()
        self.apply_theme(new_config.get("theme", DEFAULT_THEME))
        self.reconcile_download_queue()

    def show_torrent_information(self):
        """Explain the current torrent integration limitation."""
        QMessageBox.information(
            self,
            "Torrent Info",
            "Native torrent/magnet downloading requires libtorrent or "
            "external client support.",
        )
