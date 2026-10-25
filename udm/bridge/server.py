"""Qt local-socket server that receives native-host requests in the app."""

import logging
from pathlib import Path

from PyQt6.QtCore import QObject
from PyQt6.QtNetwork import QLocalServer

from udm.bridge.protocol import (
    MAX_MESSAGE_BYTES,
    BridgeError,
    decode_line,
    encode_line,
    send_to_app,
)


def instance_is_running(socket_path):
    """Return whether another app instance answers on ``socket_path``."""
    try:
        send_to_app({"type": "ping"}, socket_path, timeout=1.0)
    except (ConnectionError, OSError, BridgeError):
        return False
    return True


class BridgeServer(QObject):
    """Serve one JSON-line request per connection on the Qt event loop.

    ``handler`` receives each decoded message and returns the reply
    dictionary. Handler exceptions become error replies so a faulty request
    cannot stop the server.
    """

    def __init__(self, handler, parent=None):
        super().__init__(parent)
        self.handler = handler
        self.server = QLocalServer(self)
        self.server.setSocketOptions(QLocalServer.SocketOption.UserAccessOption)
        self.server.newConnection.connect(self._accept)
        self._buffers = {}

    def listen(self, socket_path):
        """Start listening; return ``False`` when the socket cannot be bound.

        Callers must first confirm with :func:`instance_is_running` that no
        live instance owns the path, because a stale socket file is removed.
        """
        socket_path = str(socket_path)
        Path(socket_path).parent.mkdir(parents=True, exist_ok=True)
        QLocalServer.removeServer(socket_path)
        if not self.server.listen(socket_path):
            logging.error("Bridge listen failed: %s", self.server.errorString())
            return False
        return True

    def close(self):
        """Stop accepting connections and remove the socket file."""
        self.server.close()

    def _accept(self):
        while self.server.hasPendingConnections():
            connection = self.server.nextPendingConnection()
            self._buffers[connection] = b""
            connection.readyRead.connect(lambda c=connection: self._read(c))
            connection.disconnected.connect(lambda c=connection: self._drop(c))

    def _read(self, connection):
        buffer = self._buffers.get(connection, b"") + bytes(connection.readAll())
        if len(buffer) > MAX_MESSAGE_BYTES:
            self._reply(connection, {"ok": False, "error": "Message too large"})
            return
        self._buffers[connection] = buffer
        if b"\n" not in buffer:
            return
        line = buffer.split(b"\n", 1)[0]
        try:
            reply = self.handler(decode_line(line))
        except BridgeError as error:
            reply = {"ok": False, "error": str(error)}
        except Exception as error:  # Keep serving after a handler defect.
            logging.exception("Bridge handler failed")
            reply = {"ok": False, "error": str(error)}
        self._reply(connection, reply)

    def _reply(self, connection, reply):
        connection.write(encode_line(reply))
        connection.flush()
        connection.disconnectFromServer()

    def _drop(self, connection):
        self._buffers.pop(connection, None)
        connection.deleteLater()
