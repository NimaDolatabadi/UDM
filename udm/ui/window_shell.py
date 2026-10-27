"""Window construction, tray behavior, and application lifecycle."""

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

from udm import paths
from udm.torrent.engine import is_magnet
from udm.ui.dev_reload import install_style_hot_reload
from udm.ui.tabs import BulkTab, DownloadsTab, GrabberTab, TorrentsTab
from udm.ui.tray_menu import attach_tray_menu, popup_tray_menu
from udm.ui.window_presence import bring_to_front, is_in_front


class WindowShell:
    """Construct and manage the application shell."""

    def build_ui(self):
        """Build the complete window shell and connect feature controls."""
        self.resize(1000, 650)
        # Resolve the theme before the toolbar builds so its icons can be tinted
        # to the active text color; the stylesheet is applied here as well.
        self.apply_theme()
        self.watch_system_color_scheme()
        self._setup_icon_and_tray()
        self._setup_central_widgets()
        self.create_toolbar()
        self._connect_tab_controls()
        self.setAcceptDrops(True)
        self.retranslate_ui()
        # Development convenience: live-reload styling when UDM_DEV is set. The
        # watcher is retained so it is not garbage collected.
        self._style_hot_reload = install_style_hot_reload(self)

    def _setup_icon_and_tray(self):
        logo_path = paths.resource_path("logo.png")
        if not logo_path.exists():
            return
        icon = QIcon(str(logo_path))
        self.setWindowIcon(icon)
        QApplication.setWindowIcon(icon)
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self.tray_icon = QSystemTrayIcon(icon, self)
        # Retained on the window because the macOS path never hands the menu
        # to the tray icon.
        tray_menu = self.tray_menu = QMenu()
        self.tray_show_action = QAction("Show UDM", self)
        self.tray_show_action.triggered.connect(self._on_tray_show_triggered)
        tray_menu.addAction(self.tray_show_action)
        tray_menu.aboutToShow.connect(self._capture_tray_window_state)
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.quit_app)
        tray_menu.addAction(quit_action)
        attach_tray_menu(self.tray_icon, tray_menu)
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
        self.sync_queue = QTreeWidgetItem(self.queue_root, [""])
        self.queue_root.setExpanded(True)
        # Queue icons are themed line glyphs applied by refresh_action_icons so
        # they re-tint with the active theme.
        splitter.addWidget(self.queue_tree)

        self.tabs = QTabWidget()
        self.downloads_tab = DownloadsTab(lambda: self.current_theme)
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
            self.add_magnet_from_input
        )
        self.torrents_tab.magnet_input.returnPressed.connect(
            self.add_magnet_from_input
        )
        self.torrents_tab.load_torrent_button.clicked.connect(
            self.choose_torrent_file
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

    def toggle_window_visibility(self):
        """Hide the window when it is in front; otherwise bring it forward."""
        self._apply_window_toggle(is_in_front(self))

    def _capture_tray_window_state(self):
        # Captured as the menu opens: choosing a menu item can activate the
        # app, which would make a background window look frontmost.
        self._tray_window_in_front = is_in_front(self)
        self.tray_show_action.setText(
            "Hide UDM" if self._tray_window_in_front else "Show UDM"
        )

    def _on_tray_show_triggered(self):
        self._apply_window_toggle(getattr(self, "_tray_window_in_front", False))

    def _apply_window_toggle(self, in_front):
        if in_front:
            self.hide()
        else:
            bring_to_front(self)

    def on_tray_icon_activated(self, reason):
        """Show the detached menu on macOS; elsewhere toggle on a primary click."""
        if popup_tray_menu(self.tray_menu, reason):
            return
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
        self.stop_bridge()
        self.stop_torrents()
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
        self.stop_bridge()
        self.stop_torrents()
        if self.tray_icon:
            self.tray_icon.hide()
        QApplication.quit()

    def dragEnterEvent(self, event):
        """Accept drag events containing URLs or text."""
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event):
        """Add dropped HTTP links, magnet links, or ``.torrent`` files."""
        mime = event.mimeData()
        torrent_files = [
            url.toLocalFile()
            for url in mime.urls()
            if url.isLocalFile() and url.toLocalFile().lower().endswith(".torrent")
        ]
        for path in torrent_files:
            self.add_torrent_source(path)
        if not torrent_files and mime.hasText():
            text = mime.text().strip()
            if is_magnet(text):
                self.add_torrent_source(text)
            elif text.startswith(("http://", "https://")):
                self.offer_download(text)
        event.acceptProposedAction()

    def apply_start_minimized(self):
        """Schedule the initial hide after Qt finishes showing the window."""
        if self.config_manager.config.get("start_minimized", False):
            # Delaying the hide lets Qt finish native window initialization.
            QTimer.singleShot(100, self.hide)
