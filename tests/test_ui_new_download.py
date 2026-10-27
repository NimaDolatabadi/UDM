"""Offscreen tests for the new-download prompt and download progress bars."""

import os
import unittest
from unittest.mock import patch

from PyQt6 import sip

from tests.qt_support import MainWindowTestCase
from udm.capture import CaptureRequest
from udm.ui.download_roles import PROGRESS_ROLE
from udm.ui.progress_delegate import chunk_color_token
from udm.ui.window_clipboard import is_offerable_link


class NewDownloadPromptTests(MainWindowTestCase):
    def _offer(self, url, request=None):
        dialog = self.window.offer_download(url, request)
        # Closing deletes the dialog (WA_DeleteOnClose), so check first.
        self.addCleanup(lambda: sip.isdeleted(dialog) or dialog.close())
        return dialog

    def test_capture_replies_pending_and_waits_for_the_prompt(self):
        message = {"type": "download", "url": "https://cdn.example/a.zip"}
        with patch.object(self.window, "offer_download") as offer:
            reply = self.window.handle_bridge_message(message)
        self.assertEqual(reply, {"ok": True, "pending": True})
        offer.assert_called_once()
        self.assertEqual(self.window.downloads_tab.table.rowCount(), 0)

    def test_prompt_suggests_name_and_category_folder(self):
        dialog = self._offer("https://cdn.example/files/a.zip")
        self.assertEqual(dialog.name_input.text(), "a.zip")
        self.assertEqual(
            dialog.folder_input.text(),
            str(self.manager.get_category_path("a.zip")),
        )
        self.assertTrue(dialog.name_input.isEnabled())

    def test_start_now_queues_and_starts(self):
        dialog = self._offer("https://cdn.example/a.zip")
        with patch.object(self.window, "start_worker") as start:
            dialog._choose(start_now=True)
        start.assert_called_once()
        self.assertEqual(self.window.downloads_tab.table.rowCount(), 1)

    def test_download_later_queues_paused(self):
        dialog = self._offer("https://cdn.example/a.zip")
        with patch.object(self.window, "start_worker") as start:
            dialog._choose(start_now=False)
        start.assert_not_called()
        self.assertEqual(self.window.downloads_tab.table.item(0, 2).text(), "Paused")

    def test_cancel_adds_nothing(self):
        dialog = self._offer("https://cdn.example/a.zip")
        dialog.reject()
        self.assertEqual(self.window.downloads_tab.table.rowCount(), 0)

    def test_chosen_folder_keeps_server_names_in_that_folder(self):
        target = os.path.join(self.temp.name, "Chosen")
        os.makedirs(target)
        dialog = self._offer("https://cdn.example/get?id=1")
        dialog.folder_input.setText(target)
        with patch.object(self.window, "start_worker"):
            dialog._choose(start_now=False)
        download_id = self.window.downloads_tab.table.item(0, 0).data(256)
        save_path = self.window.pending_downloads[download_id][1]
        self.assertEqual(os.path.dirname(save_path), target)
        worker = self.window._create_worker(download_id, "https://cdn.example/get?id=1", save_path)
        self.assertEqual(worker.router("movie.mkv"), target)

    def test_edited_name_is_kept_exactly(self):
        dialog = self._offer("https://cdn.example/get?id=1")
        dialog.name_input.setText("mine.bin")
        with patch.object(self.window, "start_worker"):
            dialog._choose(start_now=False)
        table = self.window.downloads_tab.table
        self.assertEqual(table.item(0, 0).text(), "mine.bin")
        download_id = table.item(0, 0).data(256)
        worker = self.window._create_worker(download_id, "https://cdn.example/x", "/tmp/mine.bin")
        self.assertIsNone(worker.router)

    def test_stream_prompt_leaves_name_to_the_page_title(self):
        request = CaptureRequest.from_message(
            {"type": "stream", "url": "https://video.example/w", "title": "Clip"}
        )
        dialog = self._offer(request.url, request)
        self.assertFalse(dialog.name_input.isEnabled())
        with patch.object(self.window, "start_worker"):
            dialog._choose(start_now=False)
        self.assertEqual(self.window.downloads_tab.table.item(0, 0).text(), "Clip")

    def test_disabled_prompt_queues_directly(self):
        self.manager.config["confirm_new_downloads"] = False
        with patch.object(self.window, "start_worker") as start:
            self.assertIsNone(self.window.offer_download("https://cdn.example/a.zip"))
        start.assert_called_once()


class ProgressTests(MainWindowTestCase):
    def _row(self):
        with patch.object(self.window, "start_worker"):
            return self.window.add_to_downloads("https://cdn.example/a.zip", start_paused=True)

    def _percent(self):
        return self.window.downloads_tab.table.item(0, 1).data(PROGRESS_ROLE)

    def test_progress_percent_follows_worker_updates(self):
        download_id = self._row()
        self.assertIsNone(self._percent())
        self.window.on_worker_progress(download_id, 25, 100, "1 MB/s", "1s", "Downloading")
        self.assertEqual(self._percent(), 25)
        # Updates without a total, such as post-processing, keep the bar.
        self.window.on_worker_progress(download_id, 0, 0, "--", "--", "Processing")
        self.assertEqual(self._percent(), 25)
        self.window.on_worker_completed(download_id, True, "")
        self.assertEqual(self._percent(), 100)

    def test_chunk_color_reflects_status(self):
        self.assertEqual(chunk_color_token("Completed"), "status_success")
        self.assertEqual(chunk_color_token("Paused"), "status_warning")
        self.assertEqual(chunk_color_token("Downloading"), "accent")

    def test_progress_cell_paints_offscreen(self):
        download_id = self._row()
        self.window.on_worker_progress(download_id, 50, 100, "1 MB/s", "1s", "Downloading")
        self.window.show()
        self.assertFalse(self.window.downloads_tab.table.grab().isNull())


class ClipboardLinkTests(unittest.TestCase):
    def test_offerable_links(self):
        self.assertTrue(is_offerable_link("https://cdn.example/a.zip?x=1"))
        self.assertTrue(is_offerable_link("magnet:?xt=urn:btih:" + "a" * 40))
        self.assertFalse(is_offerable_link("https://example.com/page"))
        self.assertFalse(is_offerable_link("just text"))


if __name__ == "__main__":
    unittest.main()
