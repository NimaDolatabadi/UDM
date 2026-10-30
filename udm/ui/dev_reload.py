"""Optional development-time style hot reload.

Watches the theme package source files and re-applies the stylesheet when they
change, so visual tweaks appear without restarting the application. Enabled only
when the ``UDM_DEV`` environment variable is truthy. It reloads styling and token
colors, including the live icon tint; structural layout changes (dialog and tab
composition) still require a restart.
"""

import importlib
import os
from pathlib import Path

from PyQt6.QtCore import QFileSystemWatcher
from PyQt6.QtWidgets import QApplication

_THEME_DIR = Path(__file__).resolve().parent / "theme"


def _is_enabled():
    """Return whether the hot reload is switched on via ``UDM_DEV``."""
    return os.environ.get("UDM_DEV", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def install_style_hot_reload(window):
    """Install a watcher that live-reloads styling for ``window``.

    Returns the watcher, which the caller must keep referenced so it stays
    alive, or ``None`` when disabled or unavailable.
    """
    if not _is_enabled() or QApplication.instance() is None:
        return None
    files = [str(path) for path in _THEME_DIR.glob("*.py")]
    watcher = QFileSystemWatcher(files)
    watcher.fileChanged.connect(
        lambda path: _reload_styles(window, watcher, path)
    )
    return watcher


def _reload_styles(window, watcher, path):
    """Reload theme modules and re-apply the stylesheet and icon tint."""
    from udm.ui.theme import qss_chrome, qss_controls, stylesheet, tokens
    from udm.ui.theme.assets import themed_stylesheet

    # Reload fragments before the module that composes them so the rebuilt
    # stylesheet reflects edits to any of them.
    importlib.reload(tokens)
    importlib.reload(qss_controls)
    importlib.reload(qss_chrome)
    importlib.reload(stylesheet)
    theme = tokens.resolve_theme(
        getattr(window, "current_theme_option", tokens.DEFAULT_THEME),
        window._system_prefers_dark(),
    )
    window.current_theme = theme
    application = QApplication.instance()
    if application is not None:
        application.setStyleSheet(themed_stylesheet(theme))
    if getattr(window, "toolbar", None) is not None:
        window.refresh_action_icons()
    # Some editors replace the file on save, which drops the watch; re-add it.
    if path not in watcher.files():
        watcher.addPath(path)
