"""Browser-extension requests handled by the main window."""

import logging

from PyQt6.QtWidgets import QSystemTrayIcon

from udm import __version__, paths
from udm.bridge.server import BridgeServer
from udm.capture import STREAM_KIND, CaptureRequest

_CAPTURE_TYPES = ("download", "stream")


class BridgeController:
    """Receive capture requests from the native host and queue them."""

    def start_bridge(self, socket_path=None):
        """Listen for native-host connections; return whether it is listening.

        The caller must ensure no other instance owns the socket (see
        :func:`udm.bridge.server.instance_is_running`).
        """
        self.bridge_server = BridgeServer(self.handle_bridge_message, self)
        listening = self.bridge_server.listen(
            socket_path or paths.bridge_socket_path()
        )
        if not listening:
            self.bridge_server = None
        return listening

    def stop_bridge(self):
        """Close the bridge socket if it is open."""
        server = getattr(self, "bridge_server", None)
        if server is not None:
            server.close()
            self.bridge_server = None

    def handle_bridge_message(self, message):
        """Apply one bridge message and return the reply sent to the browser."""
        kind = message.get("type")
        if kind == "ping":
            return {"ok": True, "running": True, "version": __version__}
        if kind == "show":
            self.reveal_window()
            return {"ok": True}
        if kind not in _CAPTURE_TYPES:
            return {"ok": False, "error": f"Unsupported message type: {kind!r}"}
        try:
            request = CaptureRequest.from_message(message)
        except ValueError as error:
            logging.warning("Rejected bridge message: %s", error)
            return {"ok": False, "error": str(error)}
        # Like a download manager's "Download Later", captures join the list
        # paused so the user starts them from the queue.
        paused = not self.config_manager.config.get("capture_autostart", False)
        if request.kind == STREAM_KIND:
            self.add_stream(request, start_paused=paused)
        else:
            self.add_to_downloads(request.url, start_paused=paused, request=request)
        self._announce_capture(request, paused)
        return {"ok": True, "paused": paused}

    def reveal_window(self):
        """Show, raise, and focus the main window."""
        self.show()
        self.raise_()
        self.activateWindow()

    def _announce_capture(self, request, paused):
        if self.tray_icon is not None and self.tray_icon.isVisible():
            detail = "Paused - press Resume to start" if paused else "Downloading"
            self.tray_icon.showMessage(
                "Added to UDM download list",
                f"{request.display_name()}\n{detail}",
                QSystemTrayIcon.MessageIcon.Information,
                3000,
            )
