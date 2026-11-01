"""Options page for getting the browser extension and checking its connection."""

import logging

from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QMessageBox,
    QPushButton,
    QWidget,
)

from udm.bridge import connection_status, installer
from udm.bridge.browsers import CHROMIUM, SAFARI, supported_browsers
from udm.constants import RELEASES_URL
from udm.ui.extension_install_dialog import confirm_install
from udm.ui.settings_layout import (
    SCALE,
    add_form_row,
    muted_label,
    section_label,
    settings_form,
    settings_page,
)


def _open_url(url):
    QDesktopServices.openUrl(QUrl(url))


def connection_text(browser, entries):
    """Return the status sentence for ``browser`` and whether it connected."""
    described = connection_status.describe(entries.get(browser.engine))
    if described is None:
        return (f"Not connected yet. After adding UDM Capture to {browser.name}, "
                "open its toolbar popup once."), False
    if browser.engine == CHROMIUM:
        # One extension build serves every Chromium browser, so the record
        # cannot tell them apart.
        return f"In a Chromium-based browser, {described}", True
    return described, True


def get_note(browser):
    """Return what the Get button does for ``browser``."""
    if browser.engine == SAFARI:
        return ("Safari loads UDM Capture from an app that UDM creates on this "
                "Mac. UDM explains what it does and asks first.")
    if browser.store_url:
        return f"Opens the UDM Capture listing for {browser.name}."
    return ("UDM Capture is not in browser stores yet. This opens the UDM "
            "releases page, which has the extension file for testing. Until a "
            "store listing exists, install from source below.")


class BrowserIntegrationPage(QWidget):
    """Get the extension for a chosen browser and show its connection.

    UDM registers its browser helper at every launch, so a store install
    needs nothing else. Installing from source acts immediately rather than
    on OK, because it writes browser files instead of changing a stored
    setting, and it asks for confirmation first.
    """

    def __init__(self, config, parent=None, install=None, open_pages=None,
                 confirm=None, open_url=None, load_status=None):
        super().__init__(parent)
        self._install = install or installer.install
        self._open_pages = open_pages or installer.open_setup_pages
        self._confirm = confirm or confirm_install
        self._open_url = open_url or _open_url
        self._load_status = load_status or connection_status.load
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
        browsers = supported_browsers()
        # Installed browsers come first so the likely choice is preselected.
        for browser in sorted(browsers, key=lambda item: not item.is_installed()):
            label = browser.name if browser.is_installed() else f"{browser.name} (not found)"
            self.browser.addItem(label, browser)
        add_form_row(form, "Browser", self.browser)

        self.connection = muted_label("")
        self.check_button = QPushButton("Check Again")
        self.check_button.setAutoDefault(False)
        self.check_button.clicked.connect(self.refresh)
        add_form_row(
            form, "Status", self._row(self.connection, self.check_button, fill=True)
        )

        self.get_button = QPushButton("Get UDM Capture...")
        self.get_button.setAutoDefault(False)
        self.get_button.clicked.connect(self.get_extension)
        add_form_row(form, "Extension", self._row(self.get_button))
        outer.addLayout(form)
        self.get_note = muted_label("")
        outer.addWidget(self.get_note)
        outer.addWidget(muted_label(
            "UDM connects to installed browsers automatically each time it starts."
        ))

        self.developer_heading = section_label("Developers")
        outer.addWidget(self.developer_heading)
        self.developer_note = muted_label(
            "Build the extension from this copy of UDM and load it unpacked. "
            "The browser keeps it only in Developer mode (Chromium) or until it "
            "quits (Firefox)."
        )
        outer.addWidget(self.developer_note)
        self.install_button = QPushButton("Install from Source...")
        self.install_button.setAutoDefault(False)
        self.install_button.clicked.connect(self.install_selected)
        self.install_row = QWidget()
        self.install_row.setLayout(self._row(self.install_button))
        outer.addWidget(self.install_row)

        self.status = muted_label("")
        outer.addWidget(self.status)
        outer.addStretch(1)
        self.browser.currentIndexChanged.connect(self.refresh)
        self.refresh()

    @staticmethod
    def _row(*widgets, fill=False):
        """Return a row of ``widgets``; with ``fill`` the first one stretches."""
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(SCALE.space_sm)
        for index, widget in enumerate(widgets):
            row.addWidget(widget, 1 if fill and index == 0 else 0)
        if not fill:
            row.addStretch(1)
        return row

    def selected_browser(self):
        """Return the browser chosen in the selector."""
        return self.browser.currentData()

    def showEvent(self, event):
        """Refresh the connection status whenever the page appears."""
        super().showEvent(event)
        self.refresh()

    def refresh(self):
        """Update the status and buttons for the selected browser."""
        browser = self.selected_browser()
        if browser is None:
            return
        text, connected = connection_text(browser, self._load_status())
        self.connection.setText(text)
        self.connection.setProperty("tone", "success" if connected else "")
        self.connection.setProperty("muted", not connected)
        self.connection.style().unpolish(self.connection)
        self.connection.style().polish(self.connection)
        safari = browser.engine == SAFARI
        self.get_button.setText("Install for Safari..." if safari else "Get UDM Capture...")
        self.get_note.setText(get_note(browser))
        # Safari's only install is the source build, so the Get button does it.
        for widget in (self.developer_heading, self.developer_note, self.install_row):
            widget.setVisible(not safari)

    def get_extension(self):
        """Open the store listing or release page, or install for Safari."""
        browser = self.selected_browser()
        if browser.engine == SAFARI:
            return self.install_selected()
        self._open_url(browser.store_url or RELEASES_URL)
        return None

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
        except OSError as error:
            logging.warning("Could not open browser setup pages: %s", error)
        QMessageBox.information(
            self,
            "Finish in Your Browser",
            f"UDM prepared {browser.name}.\n\n{steps}",
        )
        return result
