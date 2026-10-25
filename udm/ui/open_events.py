"""Route macOS open requests for magnet links and torrent files to the window.

The app bundle registers the ``magnet`` URL scheme and the ``.torrent``
document type, so clicking a magnet link in a browser or opening a torrent in
Finder delivers a ``QFileOpenEvent`` to the running application.
"""

from PyQt6.QtCore import QEvent, QObject

from udm.torrent.engine import is_magnet


def torrent_source_from_url(url):
    """Return a magnet URI or local ``.torrent`` path for a ``QUrl``, else ``None``."""
    if url.scheme().lower() == "magnet":
        text = url.toString()
        return text if is_magnet(text) else None
    if url.isLocalFile() and url.toLocalFile().lower().endswith(".torrent"):
        return url.toLocalFile()
    return None


class OpenEventFilter(QObject):
    """Application event filter that adds opened torrents to ``window``."""

    def __init__(self, window):
        super().__init__(window)
        self.window = window

    def eventFilter(self, watched, event):
        """Consume file-open events that carry a torrent source."""
        if event.type() != QEvent.Type.FileOpen:
            return False
        source = torrent_source_from_url(event.url())
        if source is None:
            return False
        self.window.reveal_window()
        self.window.add_torrent_source(source)
        return True
