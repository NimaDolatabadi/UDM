"""Theme resolution and live application for the main window.

Mixed into the main window to keep theme concerns separate from window
construction. Resolves the selected theme option, following the operating
system's light or dark preference when the System option is active, and applies
the stylesheet application-wide so open dialogs restyle together.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from udm.ui.theme import (
    DEFAULT_THEME,
    SYSTEM_OPTION,
    resolve_theme,
)
from udm.ui.theme.assets import themed_stylesheet


class ThemeController:
    """Apply and live-update the active theme for the window and its dialogs."""

    def apply_theme(self, theme_option=None):
        """Apply the selected theme application-wide and re-tint icons.

        ``theme_option`` is a value from the theme selector. The ``System``
        option resolves to a concrete theme from the operating system's dark or
        light preference; a concrete name applies directly. The stylesheet is set
        on the ``QApplication`` so open dialogs restyle alongside the main window.
        Passing ``None`` reads the persisted selection from configuration.
        """
        if theme_option is None:
            theme_option = self.config_manager.config.get("theme", DEFAULT_THEME)
        self.current_theme_option = theme_option
        self.current_theme = resolve_theme(
            theme_option, self._system_prefers_dark()
        )
        application = QApplication.instance()
        if application is not None:
            application.setStyleSheet(themed_stylesheet(self.current_theme))
        # Toolbar icons only exist after create_toolbar; guard the initial call
        # made before the toolbar is built.
        if getattr(self, "toolbar", None) is not None:
            self.refresh_action_icons()

    @staticmethod
    def _system_prefers_dark():
        """Return whether the OS requests a dark scheme.

        Treats an unknown scheme (for example headless environments) as dark to
        match the application's dark-first default.
        """
        application = QApplication.instance()
        if application is None:
            return True
        return application.styleHints().colorScheme() != Qt.ColorScheme.Light

    def watch_system_color_scheme(self):
        """React to OS light/dark changes while the System option is active."""
        application = QApplication.instance()
        if application is None:
            return
        application.styleHints().colorSchemeChanged.connect(
            self._on_system_color_scheme_changed
        )

    def _on_system_color_scheme_changed(self, _scheme):
        """Restyle live when the OS scheme changes and System is selected."""
        if getattr(self, "current_theme_option", None) == SYSTEM_OPTION:
            self.apply_theme(SYSTEM_OPTION)
