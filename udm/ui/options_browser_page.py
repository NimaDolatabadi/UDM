"""Options page for installing the browser extension and stream settings."""

import logging
import subprocess

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QMessageBox,
    QPushButton,
    QWidget,
)

from udm.bridge import installer
from udm.bridge.browsers import BROWSERS
from udm.constants import DEFAULT_CONFIG, STREAM_QUALITY_OPTIONS
from udm.ui.settings_layout import SCALE, muted_label, settings_form, settings_page


class BrowserIntegrationPage(QWidget):
    """Install the extension into a chosen browser and pick stream quality.

    Installing acts immediately rather than on OK, because it writes browser
    files instead of changing a stored setting.
    """

    def __init__(self, config, parent=None, install=None, open_pages=None):
        super().__init__(parent)
        self._install = install or installer.install
        self._open_pages = open_pages or installer.open_setup_pages
        page, outer = settings_page("Browser Integration")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(page)

        outer.addWidget(muted_label(
            "The UDM Capture extension sends browser downloads and playing "
            "videos to UDM, and adds a Download button on top of videos."
        ))
        form = settings_form()
        self.browser = QComboBox()
        self.browser.setMinimumWidth(220)
        # Installed browsers come first so the likely choice is preselected.
        ordered = sorted(BROWSERS, key=lambda item: not item.is_installed())
        for browser in ordered:
            label = browser.name if browser.is_installed() else f"{browser.name} (not found)"
            self.browser.addItem(label, browser)
        self.quality = QComboBox()
        self.quality.setMinimumWidth(220)
        self.quality.addItems(STREAM_QUALITY_OPTIONS)
        self.quality.setCurrentText(
            config.get("stream_quality", DEFAULT_CONFIG["stream_quality"])
        )
        form.addRow("Browser:", self.browser)
        form.addRow("Default video quality:", self.quality)
        outer.addLayout(form)
        self.autostart = QCheckBox("Start captured downloads immediately")
        self.autostart.setChecked(bool(config.get("capture_autostart", False)))
        outer.addWidget(self.autostart)
        outer.addWidget(muted_label(
            "When off, captured links join the download list paused; start "
            "them with Resume. The quality chosen in the browser overrides the "
            "default."
        ))

        buttons = QHBoxLayout()
        buttons.setSpacing(SCALE.space_sm)
        self.install_button = QPushButton("Install Extension")
        self.install_button.clicked.connect(self.install_selected)
        buttons.addWidget(self.install_button)
        buttons.addStretch(1)
        outer.addLayout(buttons)

        self.status = muted_label(
            "Installing prepares the extension folder and the connection to "
            "UDM, then opens the browser so you can load it."
        )
        outer.addWidget(self.status)
        outer.addStretch(1)

    def selected_browser(self):
        """Return the browser chosen in the selector."""
        return self.browser.currentData()

    def install_selected(self):
        """Install for the selected browser and show the remaining steps."""
        browser = self.selected_browser()
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

    def values(self):
        """Return the settings owned by this page."""
        return {
            "stream_quality": self.quality.currentText(),
            "capture_autostart": self.autostart.isChecked(),
        }
