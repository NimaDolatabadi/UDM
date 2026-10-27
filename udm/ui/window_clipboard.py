"""Offer magnet and file links copied to the clipboard as downloads."""

from PyQt6.QtWidgets import QApplication, QMessageBox

from udm.constants import DOWNLOAD_EXTENSIONS
from udm.torrent.engine import is_magnet


def is_offerable_link(text):
    """Return whether clipboard ``text`` is a magnet or a known file link."""
    if is_magnet(text):
        return True
    return text.startswith(("http://", "https://")) and text.lower().split(
        "?", 1
    )[0].endswith(DOWNLOAD_EXTENSIONS)


class ClipboardController:
    """Watch the clipboard while the Options setting is enabled."""

    def setup_clipboard_monitor(self):
        """Connect clipboard discovery once, even after repeated option changes."""
        if self.clipboard is not None:
            return
        self.clipboard = QApplication.clipboard()
        self.clipboard.dataChanged.connect(self.on_clipboard_change)
        self.last_clipboard_text = ""

    def teardown_clipboard_monitor(self):
        """Disconnect clipboard discovery when the option is disabled."""
        if self.clipboard is not None:
            self.clipboard.dataChanged.disconnect(self.on_clipboard_change)
            self.clipboard = None

    def on_clipboard_change(self):
        """Offer copied magnet links and supported HTTP file links."""
        if not self.config_manager.config.get("clipboard_monitor", False):
            return
        text = self.clipboard.text().strip()
        if not text or text == self.last_clipboard_text or not is_offerable_link(text):
            return
        self.last_clipboard_text = text
        magnet = is_magnet(text)
        if not magnet and self.prompts_for_downloads():
            # The new-download prompt has its own Cancel, so it replaces the
            # yes/no question.
            self.offer_download(text)
            return
        # The question dialog can itself affect clipboard state on some desktop
        # environments. Blocking signals prevents a recursive prompt.
        self.clipboard.blockSignals(True)
        try:
            kind = "magnet link" if magnet else "file link"
            answer = QMessageBox.question(
                self,
                "Download Detected",
                f"Detected a {kind} in clipboard:\n{text}\n\n"
                "Add to downloads?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if answer == QMessageBox.StandardButton.Yes:
                if magnet:
                    self.add_torrent_source(text)
                else:
                    self.add_to_downloads(text)
        finally:
            self.clipboard.blockSignals(False)
