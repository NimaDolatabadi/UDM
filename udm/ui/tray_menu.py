"""Tray icon menu wiring that avoids the native macOS status item menu.

On macOS 27, Qt's Cocoa plugin crashes when a menu attached through
``QSystemTrayIcon.setContextMenu`` opens: its menu-tracking observer reads
``clickCount`` from a current event that is no longer a mouse event, and
AppKit aborts the process. On macOS the menu is therefore never attached
natively; it is popped up at the cursor from the ``activated`` signal instead.
"""

import sys

from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import QMenu, QSystemTrayIcon

_POPUP_REASONS = (
    QSystemTrayIcon.ActivationReason.Trigger,
    QSystemTrayIcon.ActivationReason.Context,
)


def uses_native_menu(platform=None):
    """Return whether the tray menu can be attached natively on ``platform``."""
    return (platform or sys.platform) != "darwin"


def attach_tray_menu(tray_icon: QSystemTrayIcon, menu: QMenu, platform=None):
    """Attach ``menu`` natively where that is safe; otherwise leave it detached."""
    if uses_native_menu(platform):
        tray_icon.setContextMenu(menu)


def popup_tray_menu(menu: QMenu, reason, platform=None) -> bool:
    """Show a detached ``menu`` for a click ``reason``.

    Returns True when the menu was shown, meaning the activation is handled
    and must not also toggle the window.
    """
    if uses_native_menu(platform) or reason not in _POPUP_REASONS:
        return False
    menu.popup(QCursor.pos())
    return True
