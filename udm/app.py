"""Qt application creation and process entry point."""

import logging
import os
import sys

from PyQt6.QtWidgets import QApplication

from udm.ui.main_window import MainWindow


def create_application(argv=None, config_manager=None, register_startup=True):
    """Create or reuse the Qt application and construct the main window."""
    application = QApplication.instance() or QApplication(argv or sys.argv)
    if os.environ.get("QT_QPA_PLATFORM") == "offscreen":
        application.setStyle("Fusion")
    elif sys.platform == "darwin":
        application.setStyle("macOS")
    application.setQuitOnLastWindowClosed(True)
    window = MainWindow(
        config_manager=config_manager,
        register_startup=register_startup,
    )
    return application, window


def main():
    """Run the desktop application."""
    logging.basicConfig(
        filename="download_manager.log",
        level=logging.INFO,
    )
    application, window = create_application()
    window.show()
    return application.exec()
