"""Tests for bridge framing, socket transport, and the native host."""

import io
from pathlib import Path
import socket
import struct
import tempfile
import threading
import unittest

from udm.bridge import native_host
from udm.bridge.protocol import (
    MAX_MESSAGE_BYTES,
    BridgeError,
    decode_line,
    encode_line,
    read_native_message,
    send_to_app,
    write_native_message,
)


def framed(*messages):
    stream = io.BytesIO()
    for message in messages:
        write_native_message(stream, message)
    stream.seek(0)
    return stream


class FakeApp:
    """Answer JSON-line requests on a Unix socket from a background thread."""

    def __init__(self, path, reply):
        self.received = []
        self.server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.server.bind(str(path))
        self.server.listen()
        self.reply = reply
        self.thread = threading.Thread(target=self._serve, daemon=True)
        self.thread.start()

    def _serve(self):
        while True:
            try:
                connection, _ = self.server.accept()
            except OSError:
                return
            with connection:
                data = b""
                while b"\n" not in data:
                    data += connection.recv(4096)
                self.received.append(decode_line(data))
                connection.sendall(encode_line(self.reply))

    def close(self):
        self.server.close()


class ProtocolTests(unittest.TestCase):
    def test_native_frames_round_trip_and_end_cleanly(self):
        stream = framed({"type": "ping"}, {"url": "https://e.com/ü"})
        self.assertEqual(read_native_message(stream), {"type": "ping"})
        self.assertEqual(read_native_message(stream), {"url": "https://e.com/ü"})
        self.assertIsNone(read_native_message(stream))

    def test_oversized_truncated_and_non_object_frames_are_rejected(self):
        oversized = io.BytesIO(struct.pack("=I", MAX_MESSAGE_BYTES + 1))
        truncated = io.BytesIO(struct.pack("=I", 10) + b"{}")
        array = io.BytesIO(struct.pack("=I", 2) + b"[]")
        for stream in (oversized, truncated, array):
            with self.assertRaises(BridgeError):
                read_native_message(stream)

    def test_send_to_app_round_trips_over_unix_socket(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "bridge.sock"
            app = FakeApp(path, {"ok": True})
            try:
                reply = send_to_app({"type": "ping"}, path)
            finally:
                app.close()
            self.assertEqual(reply, {"ok": True})
            self.assertEqual(app.received, [{"type": "ping"}])

    def test_send_to_app_without_listener_raises_connection_error(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ConnectionError):
                send_to_app({"type": "ping"}, Path(temp) / "missing.sock")


class NativeHostTests(unittest.TestCase):
    def test_ping_reports_closed_app_without_launching(self):
        launches = []
        with tempfile.TemporaryDirectory() as temp:
            stdout = io.BytesIO()
            code = native_host.run(
                framed({"type": "ping"}),
                stdout,
                Path(temp) / "none.sock",
                lambda: launches.append(True),
            )
        stdout.seek(0)
        self.assertEqual(code, 0)
        self.assertEqual(
            read_native_message(stdout),
            {"ok": True, "host": True, "running": False},
        )
        self.assertEqual(launches, [])

    def test_download_launches_app_then_forwards_message(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "bridge.sock"
            apps = []

            def launch():
                apps.append(FakeApp(path, {"ok": True}))

            message = {"type": "download", "url": "https://e.com/a.zip"}
            reply = native_host.handle(message, path, launch)
            for app in apps:
                app.close()
        self.assertEqual(reply, {"ok": True})
        self.assertEqual(apps[0].received, [message])

    def test_formats_are_answered_by_the_host_without_the_app(self):
        launches = []
        reply = native_host.handle(
            {"type": "formats", "url": "https://v.example/w"},
            "/nonexistent.sock",
            lambda: launches.append(True),
            lambda message: {"ok": True, "qualities": [{"quality": "720p"}]},
        )
        self.assertEqual(reply["qualities"], [{"quality": "720p"}])
        self.assertEqual(launches, [])

    def test_probe_rejects_invalid_requests(self):
        reply = native_host.probe_formats({"type": "formats", "url": "file:///etc/passwd"})
        self.assertFalse(reply["ok"])

    def test_malformed_frame_returns_error_and_exit_code(self):
        stdout = io.BytesIO()
        code = native_host.run(
            io.BytesIO(struct.pack("=I", 3) + b"{x}"), stdout, "/nonexistent", None
        )
        stdout.seek(0)
        self.assertEqual(code, 1)
        self.assertFalse(read_native_message(stdout)["ok"])


if __name__ == "__main__":
    unittest.main()
