"""Tests for protocol compatibility, the Windows pipe client, and contact records."""

from datetime import datetime, timedelta, timezone
import io
import tempfile
import unittest

from udm.bridge import connection_status, native_host
from udm.bridge.protocol import (
    MIN_PROTOCOL_VERSION,
    PROTOCOL_VERSION,
    BridgeError,
    compatibility_error,
    encode_line,
    exchange_over_pipe,
    read_native_message,
    write_native_message,
)


class FakePipe(io.BytesIO):
    """A pipe that records what was written and returns a canned reply."""

    def __init__(self, reply):
        super().__init__()
        self.reply = io.BytesIO(reply)
        self.written = b""

    def write(self, data):
        self.written += data
        return len(data)

    def read(self, size=-1):
        return self.reply.read(size)


class CompatibilityTests(unittest.TestCase):
    def test_unversioned_and_current_messages_are_accepted(self):
        self.assertIsNone(compatibility_error({"type": "download"}))
        self.assertIsNone(compatibility_error(
            {"protocol": PROTOCOL_VERSION, "minProtocol": MIN_PROTOCOL_VERSION}
        ))

    def test_each_side_is_told_what_to_update(self):
        old = compatibility_error({"protocol": MIN_PROTOCOL_VERSION - 1})
        self.assertIn("Update the extension", old)
        newer = compatibility_error({"protocol": 99, "minProtocol": PROTOCOL_VERSION + 1})
        self.assertIn("Update UDM", newer)

    def test_malformed_versions_count_as_version_one(self):
        self.assertIsNone(compatibility_error({"protocol": "2", "minProtocol": True}))

    def test_native_host_refuses_incompatible_requests_before_probing(self):
        probes = []
        reply = native_host.handle(
            {"type": "formats", "url": "https://v.example/w", "protocol": 0},
            "/nonexistent.sock", None, probes.append,
        )
        self.assertTrue(reply["incompatible"])
        self.assertEqual(probes, [])

    def test_host_records_each_message_it_reads(self):
        recorded = []
        stream = io.BytesIO()
        write_native_message(stream, {"type": "ping", "engine": "firefox"})
        stream.seek(0)
        output = io.BytesIO()
        native_host.run(stream, output, "/nonexistent.sock", None, recorder=recorded.append)
        output.seek(0)
        self.assertEqual(recorded, [{"type": "ping", "engine": "firefox"}])
        self.assertTrue(read_native_message(output)["ok"])


class PipeClientTests(unittest.TestCase):
    def test_exchange_writes_one_line_and_reads_the_reply(self):
        pipe = FakePipe(encode_line({"ok": True}))
        reply = exchange_over_pipe({"type": "ping"}, r"\\.\pipe\udm", opener=lambda *a, **k: pipe)
        self.assertEqual(reply, {"ok": True})
        self.assertEqual(pipe.written, encode_line({"type": "ping"}))

    def test_missing_pipe_is_a_connection_error(self):
        def opener(*args, **kwargs):
            raise FileNotFoundError("no pipe")

        with self.assertRaises(ConnectionError):
            exchange_over_pipe({"type": "ping"}, r"\\.\pipe\udm", opener=opener)

    def test_empty_reply_is_a_bridge_error(self):
        with self.assertRaises(BridgeError):
            exchange_over_pipe(
                {"type": "ping"}, r"\\.\pipe\udm", opener=lambda *a, **k: FakePipe(b"")
            )


class ConnectionStatusTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

    def test_record_keeps_the_latest_contact_per_engine(self):
        now = datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc)
        message = {"engine": "firefox", "extensionVersion": "1.0", "protocol": 1}
        self.assertTrue(connection_status.record(message, self.temp.name, now))
        later = {**message, "extensionVersion": "1.1"}
        connection_status.record(later, self.temp.name, now + timedelta(hours=2))
        entries = connection_status.load(self.temp.name)
        self.assertEqual(entries["firefox"]["version"], "1.1")
        self.assertEqual(
            connection_status.describe(entries["firefox"], now + timedelta(hours=5)),
            "UDM Capture 1.1 last connected 3 hours ago.",
        )

    def test_messages_without_a_known_engine_are_ignored(self):
        self.assertFalse(connection_status.record({"type": "ping"}, self.temp.name))
        self.assertFalse(connection_status.record({"engine": "x"}, self.temp.name))
        self.assertEqual(connection_status.load(self.temp.name), {})

    def test_unreadable_records_describe_nothing(self):
        self.assertIsNone(connection_status.describe(None))
        self.assertIsNone(connection_status.describe({"seen": "yesterday"}))


if __name__ == "__main__":
    unittest.main()
