"""Offscreen tests for the bridge server and capture handling."""

from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from tests.qt_support import MainWindowTestCase, QtTestCase
from udm.bridge.protocol import MIN_PROTOCOL_VERSION, PROTOCOL_VERSION, send_to_app
from udm.bridge.server import BridgeServer, instance_is_running
from udm.capture import CaptureRequest
from udm.workers import DownloadWorker, StreamWorker


class BridgeServerTests(QtTestCase):
    def _call(self, server_path, message):
        result = {}
        thread = threading.Thread(
            target=lambda: result.update(reply=send_to_app(message, server_path)),
            daemon=True,
        )
        thread.start()
        deadline = time.monotonic() + 5
        while thread.is_alive() and time.monotonic() < deadline:
            self.application.processEvents()
            time.sleep(0.01)
        return result.get("reply")

    def test_server_replies_and_survives_handler_errors(self):
        def handler(message):
            if message.get("type") == "boom":
                raise RuntimeError("broken")
            return {"ok": True, "echo": message["type"]}

        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "bridge.sock"
            server = BridgeServer(handler)
            self.assertTrue(server.listen(path))
            try:
                self.assertEqual(self._call(path, {"type": "ping"}), {"ok": True, "echo": "ping"})
                self.assertEqual(self._call(path, {"type": "boom"}), {"ok": False, "error": "broken"})
                self.assertEqual(self._call(path, {"type": "again"})["echo"], "again")
            finally:
                server.close()
            self.assertFalse(instance_is_running(path))

    def test_background_types_reply_from_a_worker_thread(self):
        main = threading.get_ident()
        threads = []

        def probe(message):
            threads.append(threading.get_ident())
            return {"ok": True, "qualities": [message["url"]]}

        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "bridge.sock"
            server = BridgeServer(lambda m: {"ok": True}, background={"formats": probe})
            self.assertTrue(server.listen(path))
            try:
                reply = self._call(path, {"type": "formats", "url": "https://v.example/w"})
                self.assertEqual(reply["qualities"], ["https://v.example/w"])
                self.assertEqual(self._call(path, {"type": "ping"}), {"ok": True})
            finally:
                server.close()
        self.assertNotEqual(threads, [main])


class CaptureHandlingTests(MainWindowTestCase):
    def test_ping_and_invalid_messages(self):
        self.assertTrue(self.window.handle_bridge_message({"type": "ping"})["running"])
        reply = self.window.handle_bridge_message({"type": "download", "url": "ftp://x"})
        self.assertFalse(reply["ok"])
        self.assertEqual(self.window.downloads_tab.table.rowCount(), 0)

    def test_ping_reports_protocol_and_old_extensions_are_refused(self):
        reply = self.window.handle_bridge_message({"type": "ping"})
        self.assertEqual(reply["protocol"], PROTOCOL_VERSION)
        self.assertEqual(reply["minProtocol"], MIN_PROTOCOL_VERSION)
        message = {"type": "download", "url": "https://e.com/a.zip", "protocol": 0}
        with patch.object(self.window, "queue_download") as queue:
            reply = self.window.handle_bridge_message(message)
        queue.assert_not_called()
        self.assertTrue(reply["incompatible"])
        self.assertIn("Update the extension", reply["error"])

    def test_safari_contacts_are_recorded_by_the_app(self):
        with patch("udm.ui.window_bridge.connection_status.record") as record:
            self.window.handle_bridge_message({"type": "ping", "engine": "safari"})
            self.window.handle_bridge_message({"type": "ping", "engine": "chromium"})
        record.assert_called_once()

    def test_download_capture_queues_file_with_browser_headers(self):
        message = {
            "type": "download", "url": "https://cdn.example/get?id=1",
            "filename": "report.pdf", "cookies": "sid=9", "referrer": "https://example.com/",
        }
        self.manager.config["confirm_new_downloads"] = False
        with patch.object(self.window, "start_worker"):
            self.assertTrue(self.window.handle_bridge_message(message)["ok"])
        table = self.window.downloads_tab.table
        self.assertEqual(table.item(0, 0).text(), "report.pdf")
        download_id = table.item(0, 0).data(256)
        worker = self.window._create_worker(download_id, message["url"], "/tmp/report.pdf")
        self.assertIsInstance(worker, DownloadWorker)
        self.assertEqual(worker.headers["Cookie"], "sid=9")
        self.assertEqual(worker.headers["Referer"], "https://example.com/")

    def test_captures_join_list_paused_unless_autostart_is_on(self):
        message = {"type": "download", "url": "https://cdn.example/a.zip"}
        self.manager.config["confirm_new_downloads"] = False
        with patch.object(self.window, "start_worker") as start:
            reply = self.window.handle_bridge_message(message)
            self.assertTrue(reply["paused"])
            start.assert_not_called()
            self.assertEqual(self.window.downloads_tab.table.item(0, 2).text(), "Paused")
            self.manager.config["capture_autostart"] = True
            reply = self.window.handle_bridge_message(message)
            self.assertFalse(reply["paused"])
            start.assert_called_once()

    def test_app_rejects_formats_requests(self):
        reply = self.window.handle_bridge_message({"type": "formats", "url": "https://v.example"})
        self.assertFalse(reply["ok"])
        self.assertEqual(self.window.downloads_tab.table.rowCount(), 0)

    def test_requested_quality_overrides_default(self):
        request = CaptureRequest.from_message(
            {"type": "stream", "url": "https://video.example/w", "quality": "720p"}
        )
        download_id = self.window.add_stream(request, start_paused=True)
        worker = self.window._create_worker(download_id, request.url, "/tmp/Videos")
        self.assertEqual(worker.quality, "720p")

    def test_stream_capture_creates_stream_worker_and_renames_row(self):
        self.manager.config["stream_quality"] = "480p"
        request = CaptureRequest.from_message(
            {"type": "stream", "url": "https://video.example/watch?v=1", "title": "Clip"}
        )
        with patch.object(self.window, "start_worker"):
            download_id = self.window.add_stream(request)
        table = self.window.downloads_tab.table
        self.assertEqual(table.item(0, 0).text(), "Clip")
        worker = self.window._create_worker(download_id, request.url, "/tmp/Videos")
        self.assertIsInstance(worker, StreamWorker)
        self.assertEqual(worker.quality, "480p")
        self.window.on_worker_renamed(download_id, "Real Title")
        self.assertEqual(table.item(0, 0).text(), "Real Title")


if __name__ == "__main__":
    unittest.main()
