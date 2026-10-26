"""Tests for platform-specific tray menu attachment and popup."""

import os
import unittest
from unittest.mock import MagicMock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QSystemTrayIcon

from udm.ui.tray_menu import attach_tray_menu, popup_tray_menu, uses_native_menu

Reason = QSystemTrayIcon.ActivationReason


class TrayMenuTests(unittest.TestCase):
    def test_macos_never_attaches_the_native_menu(self):
        tray, menu = MagicMock(), MagicMock()
        attach_tray_menu(tray, menu, platform="darwin")
        tray.setContextMenu.assert_not_called()
        self.assertFalse(uses_native_menu("darwin"))

    def test_other_platforms_attach_the_native_menu(self):
        for platform in ("linux", "win32"):
            tray, menu = MagicMock(), MagicMock()
            attach_tray_menu(tray, menu, platform=platform)
            tray.setContextMenu.assert_called_once_with(menu)

    def test_macos_clicks_pop_up_the_menu(self):
        for reason in (Reason.Trigger, Reason.Context):
            menu = MagicMock()
            self.assertTrue(popup_tray_menu(menu, reason, platform="darwin"))
            menu.popup.assert_called_once()

    def test_macos_double_click_does_not_pop_up_the_menu(self):
        menu = MagicMock()
        self.assertFalse(
            popup_tray_menu(menu, Reason.DoubleClick, platform="darwin")
        )
        menu.popup.assert_not_called()

    def test_native_platforms_leave_clicks_to_the_caller(self):
        menu = MagicMock()
        self.assertFalse(popup_tray_menu(menu, Reason.Trigger, platform="linux"))
        menu.popup.assert_not_called()


if __name__ == "__main__":
    unittest.main()
