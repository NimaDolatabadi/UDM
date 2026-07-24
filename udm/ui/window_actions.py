"""Toolbar, localization, and settings actions for the main window."""

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QDialog,
    QMessageBox,
    QStyle,
    QToolBar,
)

from udm.constants import DEFAULT_CONFIG
from udm.i18n import TRANSLATIONS
from udm.startup import set_system_startup
from udm.ui.options_dialog import OptionsDialog
from udm.ui.scheduler_dialog import SchedulerDialog


class WindowActions:
    """Build actions and coordinate application-level dialogs."""

    def create_toolbar(self):
        """Create shared queue, scheduler, settings, and navigation actions."""
        self.toolbar = QToolBar("Main Toolbar")
        self.toolbar.setIconSize(QSize(24, 24))
        self.toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        self.addToolBar(self.toolbar)
        style = self.style()
        self.add_action = self._action(QStyle.StandardPixmap.SP_FileIcon)
        self.resume_action = self._action(QStyle.StandardPixmap.SP_MediaPlay)
        self.stop_action = self._action(QStyle.StandardPixmap.SP_MediaPause)
        self.stop_all_action = self._action(QStyle.StandardPixmap.SP_MediaStop)
        self.delete_action = self._action(QStyle.StandardPixmap.SP_TrashIcon)
        self.delete_completed_action = self._action(
            QStyle.StandardPixmap.SP_DialogDiscardButton
        )
        self.scheduler_action = self._action(QStyle.StandardPixmap.SP_DriveNetIcon)
        self.options_action = self._action(QStyle.StandardPixmap.SP_ComputerIcon)
        self.grabber_action = self._action(
            QStyle.StandardPixmap.SP_BrowserReload
        )
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

    def _action(self, standard_icon):
        return QAction(self.style().standardIcon(standard_icon), "", self)

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
        self.reconcile_download_queue()

    def show_torrent_information(self):
        """Explain the current torrent integration limitation."""
        QMessageBox.information(
            self,
            "Torrent Info",
            "Native torrent/magnet downloading requires libtorrent or "
            "external client support.",
        )
