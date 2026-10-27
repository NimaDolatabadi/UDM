"""Offscreen tests for the bridge server, capture handling, and browser page."""

from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from tests.qt_support import MainWindowTestCase, QtTestCase
from udm.bridge.browsers import browser_by_key
from udm.bridge.installer import InstallResult
from udm.bridge.protocol import send_to_app
from udm.bridge.server import BridgeServer, instance_is_running
from udm.capture import CaptureRequest
from udm.ui.options_browser_page import BrowserIntegrationPage
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


class CaptureHandlingTests(MainWindowTestCase):
    def test_ping_and_invalid_messages(self):
        self.assertTrue(self.window.handle_bridge_message({"type": "ping"})["running"])
        reply = self.window.handle_bridge_message({"type": "download", "url": "ftp://x"})
        self.assertFalse(reply["ok"])
        self.assertEqual(self.window.downloads_tab.table.rowCount(), 0)

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


class BrowserPageTests(QtTestCase):
    def test_install_reports_steps_and_returns_quality(self):
        calls = []
        result = InstallResult(Path("/tmp/ext"), Path("/tmp/host"), (), ("Step one.",))

        def fake_install(browser):
            calls.append(browser.key)
            return result

        page = BrowserIntegrationPage(
            {"stream_quality": "720p"},
            install=fake_install,
            open_pages=lambda browser, res: calls.append("opened"),
        )
        index = page.browser.findData(browser_by_key("firefox"))
        page.browser.setCurrentIndex(index)
        with patch("udm.ui.options_browser_page.QMessageBox.information") as info:
            self.assertIs(page.install_selected(), result)
        info.assert_called_once()
        self.assertEqual(calls, ["firefox", "opened"])
        self.assertIn("1. Step one.", page.status.text())
        self.assertEqual(
            page.values(),
            {
                "stream_quality": "720p",
                "confirm_new_downloads": True,
                "capture_autostart": False,
            },
        )

    def test_install_failure_is_shown_without_dialog(self):
        def failing_install(browser):
            raise OSError("read-only")

        page = BrowserIntegrationPage({}, install=failing_install, open_pages=None)
        with patch("udm.ui.options_browser_page.QMessageBox.information") as info:
            self.assertIsNone(page.install_selected())
        info.assert_not_called()
        self.assertIn("read-only", page.status.text())


if __name__ == "__main__":
    unittest.main()
