"""Qt local-socket server that receives native-host requests in the app."""

import logging
from pathlib import Path
import threading

from PyQt6.QtCore import QObject, pyqtSignal
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
    dictionary. ``background`` maps message types to slow handlers that run
    on a worker thread, such as quality probing for Safari, whose extension
    has no native host to answer it. Handler exceptions become error replies
    so a faulty request cannot stop the server.
    """

    # Carries a background reply back to the Qt thread.
    _finished = pyqtSignal(object, object)

    def __init__(self, handler, parent=None, background=None):
        super().__init__(parent)
        self.handler = handler
        self.background = dict(background or {})
        self.server = QLocalServer(self)
        self.server.setSocketOptions(QLocalServer.SocketOption.UserAccessOption)
        self.server.newConnection.connect(self._accept)
        self._finished.connect(self._deliver)
        self._buffers = {}
        self._pending = set()

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
        if connection in self._pending:
            return
        buffer = self._buffers.get(connection, b"") + bytes(connection.readAll())
        if len(buffer) > MAX_MESSAGE_BYTES:
            self._reply(connection, {"ok": False, "error": "Message too large"})
            return
        self._buffers[connection] = buffer
        if b"\n" not in buffer:
            return
        try:
            message = decode_line(buffer.split(b"\n", 1)[0])
        except BridgeError as error:
            self._reply(connection, {"ok": False, "error": str(error)})
            return
        task = self.background.get(message.get("type"))
        if task is None:
            self._reply(connection, _run_handler(self.handler, message))
            return
        self._pending.add(connection)
        threading.Thread(
            target=lambda: self._finished.emit(connection, _run_handler(task, message)),
            daemon=True,
        ).start()

    def _deliver(self, connection, reply):
        # The client may have hung up while the task ran.
        if connection in self._pending and connection in self._buffers:
            self._reply(connection, reply)

    def _reply(self, connection, reply):
        connection.write(encode_line(reply))
        connection.flush()
        connection.disconnectFromServer()

    def _drop(self, connection):
        self._buffers.pop(connection, None)
        self._pending.discard(connection)
        connection.deleteLater()


def _run_handler(handler, message):
    try:
        return handler(message)
    except BridgeError as error:
        return {"ok": False, "error": str(error)}
    except Exception as error:  # Keep serving after a handler defect.
        logging.exception("Bridge handler failed")
        return {"ok": False, "error": str(error)}
