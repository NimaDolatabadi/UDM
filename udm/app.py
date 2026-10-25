"""Qt application creation and process entry point."""

import logging
import os
import sys

from PyQt6.QtWidgets import QApplication

from udm import paths
from udm.bridge.protocol import BridgeError, send_to_app
from udm.bridge.server import instance_is_running
from udm.tls import use_system_trust
from udm.ui.main_window import MainWindow
from udm.ui.open_events import OpenEventFilter


def create_application(argv=None, config_manager=None, sync_startup=True):
    """Create or reuse the Qt application and construct the main window."""
    application = QApplication.instance() or QApplication(argv or sys.argv)
    # Native macOS icons abort when the offscreen Qt plugin has no window server.
    # Fusion preserves widget behavior for headless tests without native calls.
    if os.environ.get("QT_QPA_PLATFORM") == "offscreen":
        application.setStyle("Fusion")
    elif sys.platform == "darwin":
        application.setStyle("macOS")
    application.setQuitOnLastWindowClosed(True)
    window = MainWindow(
        config_manager=config_manager,
        sync_startup=sync_startup,
    )
    return application, window


def main():
    """Run the desktop application, or focus the instance already running."""
    logging.basicConfig(filename=paths.log_file(), level=logging.INFO)
    use_system_trust()
    socket_path = paths.bridge_socket_path()
    if instance_is_running(socket_path):
        try:
            send_to_app({"type": "show"}, socket_path, timeout=2.0)
        except (ConnectionError, OSError, BridgeError) as error:
            logging.warning("Could not focus running instance: %s", error)
        return 0
    application, window = create_application()
    # The bridge starts only for the real app so tests never bind the socket.
    if not window.start_bridge(socket_path):
        logging.error("Browser bridge unavailable; extension capture disabled")
    # Magnet links and .torrent files opened from other apps arrive as events.
    application.installEventFilter(OpenEventFilter(window))
    window.show()
    return application.exec()
