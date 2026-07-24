"""Window construction, tray behavior, and application lifecycle."""

from pathlib import Path

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import (
    QApplication,
    QMenu,
    QSplitter,
    QSystemTrayIcon,
    QTabWidget,
    QTreeWidget,
    QTreeWidgetItem,
)

from udm.constants import DOWNLOAD_EXTENSIONS
from udm.ui.icons import create_queue_icon
from udm.ui.styles import DARK_STYLESHEET
from udm.ui.tabs import BulkTab, DownloadsTab, GrabberTab, TorrentsTab


class WindowShell:
    """Construct and manage the application shell."""

    def build_ui(self):
        """Build the complete window shell and connect feature controls."""
        self.resize(1000, 650)
        self.setStyleSheet(DARK_STYLESHEET)
        self._setup_icon_and_tray()
        self._setup_central_widgets()
        self.create_toolbar()
        self._connect_tab_controls()
        self.setAcceptDrops(True)
        self.retranslate_ui()

    def _setup_icon_and_tray(self):
        logo_path = Path(__file__).resolve().parents[2] / "logo.png"
        if not logo_path.exists():
            return
        icon = QIcon(str(logo_path))
        self.setWindowIcon(icon)
        QApplication.setWindowIcon(icon)
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self.tray_icon = QSystemTrayIcon(icon, self)
        tray_menu = QMenu()
        show_action = QAction("Show / Hide", self)
        show_action.triggered.connect(self.toggle_window_visibility)
        tray_menu.addAction(show_action)
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.quit_app)
        tray_menu.addAction(quit_action)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_icon_activated)
        if self.config_manager.config.get("close_to_tray", True):
            self.tray_icon.show()

    def _setup_central_widgets(self):
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.setCentralWidget(splitter)
        self.queue_tree = QTreeWidget()
        self.queue_tree.setHeaderHidden(True)
        self.queue_tree.setMinimumWidth(200)
        self.queue_root = QTreeWidgetItem(self.queue_tree, [""])
        self.main_queue = QTreeWidgetItem(self.queue_root, [""])
        self.main_queue.setIcon(0, create_queue_icon("yellow", 3))
        self.sync_queue = QTreeWidgetItem(self.queue_root, [""])
        self.sync_queue.setIcon(0, create_queue_icon("green", 3))
        self.queue_root.setExpanded(True)
        splitter.addWidget(self.queue_tree)

        self.tabs = QTabWidget()
        self.downloads_tab = DownloadsTab()
        self.torrents_tab = TorrentsTab()
        self.grabber_tab = GrabberTab()
        self.bulk_tab = BulkTab()
        for tab in (
            self.downloads_tab,
            self.torrents_tab,
            self.grabber_tab,
            self.bulk_tab,
        ):
            self.tabs.addTab(tab, "")
        splitter.addWidget(self.tabs)
        splitter.setSizes([200, 800])

    def _connect_tab_controls(self):
        table = self.downloads_tab.table
        table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        table.customContextMenuRequested.connect(
            self.show_download_context_menu
        )
        self.torrents_tab.add_magnet_button.clicked.connect(
            self.show_torrent_information
        )
        self.torrents_tab.load_torrent_button.clicked.connect(
            self.show_torrent_information
        )
        self.grabber_tab.start_button.clicked.connect(self.start_grabber)
        self.grabber_tab.filter_input.textChanged.connect(
            self.apply_grab_filter
        )
        self.grabber_tab.select_all_button.clicked.connect(
            self.grabber_select_all
        )
        self.grabber_tab.transfer_button.clicked.connect(
            self.grabber_transfer
        )
        self.bulk_tab.start_button.clicked.connect(self.start_bulk_download)
        self.bulk_tab.stop_button.clicked.connect(self.stop_bulk_download)
        self.bulk_tab.transfer_button.clicked.connect(
            self.bulk_transfer_to_queue
        )

    def setup_clipboard_monitor(self):
        """Connect clipboard discovery once, even after repeated option changes."""
        if self.clipboard is not None:
            return
        self.clipboard = QApplication.clipboard()
        self.clipboard.dataChanged.connect(self.on_clipboard_change)
        self.last_clipboard_text = ""

    def teardown_clipboard_monitor(self):
        """Disconnect clipboard discovery when the option is disabled."""
        if self.clipboard is not None:
            self.clipboard.dataChanged.disconnect(self.on_clipboard_change)
            self.clipboard = None

    def on_clipboard_change(self):
        """Offer supported HTTP file links copied by the user as downloads."""
        if not self.config_manager.config.get("clipboard_monitor", False):
            return
        text = self.clipboard.text().strip()
        if (
            not text
            or text == self.last_clipboard_text
            or not text.startswith(("http://", "https://"))
            or not text.lower().split("?", 1)[0].endswith(DOWNLOAD_EXTENSIONS)
        ):
            return
        self.last_clipboard_text = text
        # The question dialog can itself affect clipboard state on some desktop
        # environments. Blocking signals prevents a recursive prompt.
        self.clipboard.blockSignals(True)
        try:
            from PyQt6.QtWidgets import QMessageBox

            answer = QMessageBox.question(
                self,
                "Download Detected",
                f"Detected a file link in clipboard:\n{text}\n\n"
                "Add to downloads?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if answer == QMessageBox.StandardButton.Yes:
                self.add_to_downloads(text)
        finally:
            self.clipboard.blockSignals(False)

    def toggle_window_visibility(self):
        """Toggle between a visible window and background tray operation."""
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.raise_()
            self.activateWindow()

    def on_tray_icon_activated(self, reason):
        """Toggle the window for a primary tray-icon activation."""
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.toggle_window_visibility()

    def _notify_download_complete(self, row):
        if self.tray_icon:
            filename = self.downloads_tab.table.item(row, 0).text()
            self.tray_icon.showMessage(
                "UDM Download Complete",
                f"Successfully finished: {filename}",
                QSystemTrayIcon.MessageIcon.Information,
                3000,
            )

    def closeEvent(self, event):
        """Hide to tray when configured, otherwise stop workers and close."""
        close_to_tray = self.config_manager.config.get("close_to_tray", True)
        if close_to_tray and self.tray_icon and self.tray_icon.isVisible():
            self.hide()
            event.ignore()
            return
        self.shutdown_workers()
        if self.tray_icon:
            self.tray_icon.hide()
        event.accept()

    def shutdown_workers(self):
        """Request cancellation and briefly wait for active threads to exit."""
        workers = {
            *self.active_workers.values(),
            *self.cancelling_workers.values(),
        }
        for worker in workers:
            worker.cancel()
            worker.wait(2000)
        if self.spider and self.spider.isRunning():
            self.spider.cancel()
            self.spider.wait(2000)
        if self.bulk_spider and self.bulk_spider.isRunning():
            self.bulk_spider.cancel()
            self.bulk_spider.wait(2000)

    def quit_app(self):
        """Stop background work, hide the tray icon, and exit Qt."""
        self.shutdown_workers()
        if self.tray_icon:
            self.tray_icon.hide()
        QApplication.quit()

    def dragEnterEvent(self, event):
        """Accept drag events containing URLs or text."""
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event):
        """Add a dropped HTTP or HTTPS text value to the download queue."""
        if event.mimeData().hasText():
            text = event.mimeData().text().strip()
            if text.startswith(("http://", "https://")):
                self.add_to_downloads(text)
            event.acceptProposedAction()

    def apply_start_minimized(self):
        """Schedule the initial hide after Qt finishes showing the window."""
        if self.config_manager.config.get("start_minimized", False):
            # Delaying the hide lets Qt finish native window initialization.
            QTimer.singleShot(100, self.hide)
