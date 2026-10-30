"""Options page for installing the browser extension."""

import logging
import subprocess

from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QMessageBox,
    QPushButton,
    QWidget,
)

from udm.bridge import installer
from udm.bridge.browsers import BROWSERS
from udm.ui.extension_install_dialog import confirm_install
from udm.ui.settings_layout import (
    SCALE,
    add_form_row,
    muted_label,
    settings_form,
    settings_page,
)


class BrowserIntegrationPage(QWidget):
    """Install the extension into a chosen browser.

    Installing acts immediately rather than on OK, because it writes browser
    files instead of changing a stored setting. It asks for confirmation
    first, since it also opens the browser and Finder.
    """

    def __init__(self, config, parent=None, install=None, open_pages=None,
                 confirm=None):
        super().__init__(parent)
        self._install = install or installer.install
        self._open_pages = open_pages or installer.open_setup_pages
        self._confirm = confirm or confirm_install
        page, outer = settings_page("Browser Integration")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(page)

        outer.addWidget(muted_label(
            "The UDM Capture extension sends browser downloads and playing "
            "videos to UDM, and adds a Download button on top of videos. "
            "Choose how new downloads start in Downloads."
        ))
        form = settings_form()
        self.browser = QComboBox()
        self.browser.setMinimumWidth(SCALE.control_md * 8)
        # Installed browsers come first so the likely choice is preselected.
        ordered = sorted(BROWSERS, key=lambda item: not item.is_installed())
        for browser in ordered:
            label = browser.name if browser.is_installed() else f"{browser.name} (not found)"
            self.browser.addItem(label, browser)
        self.install_button = QPushButton("Install Extension...")
        self.install_button.setAutoDefault(False)
        self.install_button.clicked.connect(self.install_selected)
        row = QHBoxLayout()
        row.setSpacing(SCALE.space_sm)
        row.addWidget(self.browser)
        row.addWidget(self.install_button)
        row.addStretch(1)
        add_form_row(form, "Browser", row)
        outer.addLayout(form)

        self.status = muted_label(
            "UDM explains what installing does and asks before changing "
            "anything."
        )
        outer.addWidget(self.status)
        outer.addStretch(1)

    def selected_browser(self):
        """Return the browser chosen in the selector."""
        return self.browser.currentData()

    def install_selected(self):
        """Confirm, install for the selected browser, and show the steps.

        Returns the install result, or ``None`` when the user cancels or the
        install fails.
        """
        browser = self.selected_browser()
        if not self._confirm(browser, self):
            return None
        try:
            result = self._install(browser)
        except (OSError, ValueError, KeyError) as error:
            logging.error("Extension install failed: %s", error)
            self.status.setText(f"Installation failed: {error}")
            return None
        steps = "\n".join(
            f"{number}. {step}" for number, step in enumerate(result.steps, 1)
        )
        self.status.setText(
            f"Prepared for {browser.name}. Finish in the browser:\n{steps}"
        )
        try:
            self._open_pages(browser, result)
        except (OSError, subprocess.SubprocessError) as error:
            logging.warning("Could not open browser setup pages: %s", error)
        QMessageBox.information(
            self,
            "Finish in Your Browser",
            f"UDM prepared {browser.name}.\n\n{steps}",
        )
        return result
