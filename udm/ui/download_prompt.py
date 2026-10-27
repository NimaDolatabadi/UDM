"""Dialog that asks where to save a new download and when to start it."""

from dataclasses import dataclass

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from udm.ui.settings_layout import SCALE, settings_form


@dataclass(frozen=True)
class DownloadChoice:
    """The user's answer for one new download.

    ``folder`` and ``filename`` are None when the user kept the suggestion, so
    the download keeps routing by category and adopting the server's name.
    """

    start_now: bool
    folder: str | None = None
    filename: str | None = None


class DownloadPromptDialog(QDialog):
    """Offer Start Now, Download Later, or Cancel for a link or video.

    ``chosen`` carries a :class:`DownloadChoice` for Start Now and Download
    Later; Cancel closes the dialog without emitting it. ``rename`` enables
    the file-name field, which videos leave to their page title.
    """

    chosen = pyqtSignal(object)

    def __init__(self, url, name, folder, rename=True, parent=None):
        super().__init__(parent)
        self._name = name
        self._folder = folder
        self.setWindowTitle("New Download")
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        # Captures arrive while the browser is in front; keep the prompt above
        # it so the download does not wait unnoticed.
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
        self.setMinimumWidth(520)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            SCALE.space_lg, SCALE.space_lg, SCALE.space_lg, SCALE.space_lg
        )
        layout.setSpacing(SCALE.space_md)
        heading = QLabel(name)
        heading.setProperty("heading", True)
        heading.setWordWrap(True)
        layout.addWidget(heading)

        form = settings_form()
        # A read-only field scrolls long URLs instead of widening the dialog.
        source = QLineEdit(url)
        source.setReadOnly(True)
        form.addRow("Address:", source)
        self.name_input = QLineEdit(name)
        self.name_input.setEnabled(rename)
        form.addRow("File name:", self.name_input)
        self.folder_input = QLineEdit(folder)
        browse = QPushButton("Browse...")
        browse.clicked.connect(self._browse)
        folder_row = QHBoxLayout()
        folder_row.setSpacing(SCALE.space_sm)
        folder_row.addWidget(self.folder_input, 1)
        folder_row.addWidget(browse)
        form.addRow("Save to:", folder_row)
        layout.addLayout(form)

        buttons = QHBoxLayout()
        buttons.setSpacing(SCALE.space_sm)
        buttons.addStretch(1)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        later = QPushButton("Download Later")
        later.clicked.connect(lambda: self._choose(start_now=False))
        start = QPushButton("Start Now")
        start.setDefault(True)
        start.clicked.connect(lambda: self._choose(start_now=True))
        for button in (cancel, later, start):
            buttons.addWidget(button)
        layout.addLayout(buttons)
        # Without this the read-only address field takes focus and shows
        # fully selected.
        start.setFocus()

    def choice(self, start_now):
        """Return the current fields as a :class:`DownloadChoice`."""
        folder = self.folder_input.text().strip()
        name = self.name_input.text().strip()
        return DownloadChoice(
            start_now=start_now,
            folder=folder if folder and folder != self._folder else None,
            filename=name if name and name != self._name else None,
        )

    def _choose(self, start_now):
        self.chosen.emit(self.choice(start_now))
        self.accept()

    def _browse(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Save Download To", self.folder_input.text()
        )
        if folder:
            self.folder_input.setText(folder)
