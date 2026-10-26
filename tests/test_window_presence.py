"""Tests for deciding the main window's front state and restoring it."""

import os
import unittest
from unittest.mock import MagicMock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import Qt

from udm.ui.window_presence import bring_to_front, is_in_front

State = Qt.WindowState


def fake_window(visible=True, minimized=False, active=True):
    window = MagicMock()
    window.isVisible.return_value = visible
    window.isMinimized.return_value = minimized
    window.isActiveWindow.return_value = active
    return window


class WindowPresenceTests(unittest.TestCase):
    def test_active_visible_window_is_in_front(self):
        self.assertTrue(is_in_front(fake_window()))

    def test_window_behind_other_apps_is_not_in_front(self):
        self.assertFalse(is_in_front(fake_window(active=False)))

    def test_minimized_window_is_not_in_front(self):
        self.assertFalse(is_in_front(fake_window(minimized=True)))

    def test_hidden_window_is_not_in_front(self):
        self.assertFalse(is_in_front(fake_window(visible=False)))

    def test_bring_to_front_clears_only_the_minimized_flag(self):
        window = fake_window()
        window.windowState.return_value = State.WindowMinimized | State.WindowMaximized
        bring_to_front(window)
        window.setWindowState.assert_called_once_with(State.WindowMaximized)
        window.show.assert_called_once()
        window.raise_.assert_called_once()
        window.activateWindow.assert_called_once()


if __name__ == "__main__":
    unittest.main()
