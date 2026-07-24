"""Concrete main window composed from focused feature controllers."""

from PyQt6.QtWidgets import QMainWindow

from udm.config import ConfigManager
from udm.startup import set_system_startup
from udm.ui.window_actions import WindowActions
from udm.ui.window_bulk import BulkController
from udm.ui.window_downloads import DownloadController
from udm.ui.window_grabber import GrabberController
from udm.ui.window_shell import WindowShell


class MainWindow(
    WindowActions,
    BulkController,
    GrabberController,
    DownloadController,
    WindowShell,
    QMainWindow,
):
    """Umbrella Download Manager main window."""

    def __init__(self, config_manager=None, register_startup=True):
        super().__init__()
        self.config_manager = config_manager or ConfigManager()
        self.active_workers = {}
        self.bulk_spider = None
        self.spider = None
        self.tray_icon = None
        self.clipboard = None
        # Tests inject a temporary manager and disable platform registration;
        # normal launches keep the persisted startup preference synchronized.
        if register_startup:
            set_system_startup(
                self.config_manager.config.get("start_with_os", False)
            )
        self.build_ui()
        if self.config_manager.config.get("clipboard_monitor", False):
            self.setup_clipboard_monitor()
        self.apply_start_minimized()


UDMManager = MainWindow
