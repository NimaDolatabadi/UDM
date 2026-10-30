"""Confirmation shown before installing the browser extension.

Installing writes files, registers a helper with the browser, and opens apps,
so the user sees exactly what will happen and agrees before anything changes.
"""

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from udm import paths
from udm.bridge.browsers import FIREFOX, SAFARI
from udm.ui.settings_layout import SCALE, muted_label


def install_target(browser, data_dir=None):
    """Return the folder the installer writes for ``browser``."""
    data_dir = Path(data_dir or paths.data_dir())
    if browser.engine == SAFARI:
        return data_dir / "safari"
    return data_dir / "extension" / browser.engine


def install_actions(browser):
    """Return what installing for ``browser`` does, in the order it happens."""
    if browser.engine == SAFARI:
        return (
            "Create the UDM Capture app and sign it for this Mac.",
            "Open the app, which adds UDM Capture to Safari's extension "
            "settings.",
        )
    if browser.engine == FIREFOX:
        opened = "open Firefox's page for loading add-ons"
    else:
        opened = f"open {browser.name}'s extensions page"
    return (
        "Save the extension files.",
        f"Register a small helper so {browser.name} can hand downloads to UDM.",
        f"Show the extension folder in Finder and {opened}.",
    )


def finish_note(browser):
    """Return what the user still has to do after installing."""
    if browser.engine == SAFARI:
        return (
            "Safari only loads extensions you approve. Next, you allow "
            "unsigned extensions and turn on UDM Capture in Safari's "
            "settings. UDM lists the steps after installing."
        )
    return (
        "Browsers don't let apps add extensions on their own. Next, you load "
        f"the extension folder in {browser.name}. UDM lists the steps after "
        "installing."
    )


def _display_path(path):
    """Return ``path`` with the home folder shortened to ``~``."""
    try:
        return "~/" + str(Path(path).relative_to(Path.home()))
    except ValueError:
        return str(path)


class ExtensionInstallDialog(QDialog):
    """Explain an extension install for one browser and ask to continue."""

    def __init__(self, browser, data_dir=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Install Browser Extension")
        self.setMinimumWidth(480)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            SCALE.space_lg, SCALE.space_lg, SCALE.space_lg, SCALE.space_lg
        )
        layout.setSpacing(SCALE.space_md)
        heading = QLabel(f"Install UDM Capture in {browser.name}?")
        heading.setProperty("heading", True)
        heading.setWordWrap(True)
        layout.addWidget(heading)

        layout.addWidget(QLabel("UDM will:"))
        self.actions = []
        steps = QVBoxLayout()
        steps.setSpacing(SCALE.space_xs)
        for action in install_actions(browser):
            steps.addLayout(self._bullet(action))
        layout.addLayout(steps)
        layout.addWidget(muted_label(
            f"Files go to {_display_path(install_target(browser, data_dir))}"
        ))
        if not browser.is_installed():
            self.missing = QLabel(
                f"{browser.name} wasn't found in Applications. UDM prepares "
                "the files, but can't open the browser for you."
            )
            self.missing.setProperty("tone", "warning")
            self.missing.setWordWrap(True)
            layout.addWidget(self.missing)
        layout.addWidget(muted_label(finish_note(browser)))

        buttons = QHBoxLayout()
        buttons.setSpacing(SCALE.space_sm)
        buttons.addStretch(1)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        self.install_button = QPushButton("Install")
        self.install_button.setDefault(True)
        self.install_button.clicked.connect(self.accept)
        buttons.addWidget(cancel)
        buttons.addWidget(self.install_button)
        layout.addSpacing(SCALE.space_sm)
        layout.addLayout(buttons)
        self.install_button.setFocus()

    def _bullet(self, text):
        """Return a row with a bullet and text that wraps under itself."""
        row = QHBoxLayout()
        row.setSpacing(SCALE.space_sm)
        label = QLabel(text)
        label.setWordWrap(True)
        self.actions.append(label)
        row.addWidget(QLabel("•"), 0, Qt.AlignmentFlag.AlignTop)
        row.addWidget(label, 1, Qt.AlignmentFlag.AlignTop)
        return row


def confirm_install(browser, parent=None):
    """Show the confirmation for ``browser``; return whether to install."""
    dialog = ExtensionInstallDialog(browser, parent=parent)
    return dialog.exec() == QDialog.DialogCode.Accepted
