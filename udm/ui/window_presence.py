"""Decide whether the main window is in front and bring it forward."""

from PyQt6.QtCore import Qt


def is_in_front(window) -> bool:
    """Return whether ``window`` is shown, not minimized, and active.

    A window behind other applications or minimized to the Dock still reports
    ``isVisible()``, so visibility alone cannot decide a show/hide toggle.
    """
    return (
        window.isVisible()
        and not window.isMinimized()
        and window.isActiveWindow()
    )


def bring_to_front(window):
    """Show ``window`` restored from minimized, raised, and focused."""
    # macOS restores a hidden window that kept its minimized flag as an empty
    # black frame, so the flag is cleared before showing. Other state flags,
    # such as maximized, are kept.
    window.setWindowState(window.windowState() & ~Qt.WindowState.WindowMinimized)
    window.show()
    window.raise_()
    window.activateWindow()
