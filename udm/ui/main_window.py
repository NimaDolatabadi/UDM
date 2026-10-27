"""Concrete main window composed from focused feature controllers."""

from PyQt6.QtWidgets import QMainWindow

from udm.config import ConfigManager
from udm.startup import sync_system_startup
from udm.ui.window_actions import WindowActions
from udm.ui.window_bridge import BridgeController
from udm.ui.window_bulk import BulkController
from udm.ui.window_clipboard import ClipboardController
from udm.ui.window_downloads import DownloadController
from udm.ui.window_grabber import GrabberController
from udm.ui.window_shell import WindowShell
from udm.ui.window_theme import ThemeController
from udm.ui.window_torrents import TorrentController


class MainWindow(
    WindowActions,
    BridgeController,
    BulkController,
    ClipboardController,
    GrabberController,
    DownloadController,
    TorrentController,
    ThemeController,
    WindowShell,
    QMainWindow,
):
    """Umbrella Download Manager main window."""

    def __init__(self, config_manager=None, sync_startup=True):
        super().__init__()
        self.config_manager = config_manager or ConfigManager()
        self.active_workers = {}
        self.cancelling_workers = {}
        self.pending_downloads = {}
        # Captured browser requests keyed by download identifier.
        self.download_requests = {}
        # Destination routers for downloads whose folder or name the user set.
        self.download_routers = {}
        self.bridge_server = None
        self.torrent_engine = None
        self.torrent_timer = None
        # Torrents that reported completion, and those seen unfinished, so
        # only completions during this session are announced.
        self.torrent_finished = set()
        self.torrent_seen = set()
        self.manually_paused = set()
        self.bulk_spider = None
        self.spider = None
        self.tray_icon = None
        self.clipboard = None
        if sync_startup:
            sync_system_startup(
                self.config_manager.config.get("start_with_os", False)
            )
        self.build_ui()
        self.setup_download_scheduler()
        self.start_torrents()
        if self.config_manager.config.get("clipboard_monitor", False):
            self.setup_clipboard_monitor()
        self.apply_start_minimized()


UDMManager = MainWindow
