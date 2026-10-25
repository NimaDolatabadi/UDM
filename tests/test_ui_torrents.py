"""Offscreen tests for the Torrents tab controller and open-event routing."""

import unittest
from unittest.mock import patch

from PyQt6.QtCore import QUrl

from tests.qt_support import MainWindowTestCase, QtTestCase
from udm.torrent.engine import TorrentError
from udm.torrent.status import TorrentSnapshot
from udm.ui.open_events import torrent_source_from_url

MAGNET = "magnet:?xt=urn:btih:dd8255ecdc7ca55fb0bbf81323d87062db1f6d1c"


class FakeEngine:
    """Record engine calls and report one snapshot per torrent."""

    def __init__(self, state_dir):
        self.torrents = {}
        self.calls = []

    def add_magnet(self, uri, save_path):
        if "bad" in uri:
            raise TorrentError("Invalid magnet link")
        self.calls.append(("add", save_path))
        added = "abc" not in self.torrents
        self.torrents["abc"] = "Downloading"
        return "abc", added

    def add_torrent_file(self, path, save_path):
        self.torrents["file"] = "Downloading"
        return "file", True

    def pause(self, torrent_id):
        self.torrents[torrent_id] = "Paused"

    def resume(self, torrent_id):
        self.torrents[torrent_id] = "Downloading"

    def remove(self, torrent_id):
        self.torrents.pop(torrent_id, None)

    def ids(self):
        return list(self.torrents)

    def snapshots(self):
        return [
            TorrentSnapshot(key, "Movie", 2048, 1024, 0.5, state, 512, 0, 3, 1, False, 2)
            for key, state in self.torrents.items()
        ]

    def close(self):
        self.calls.append(("close",))


class TorrentControllerTests(MainWindowTestCase):
    def setUp(self):
        super().setUp()
        self.window.torrent_engine_factory = FakeEngine
        self.table = self.window.torrents_tab.table

    def _add_magnet(self, text=MAGNET):
        self.window.torrents_tab.magnet_input.setText(text)
        self.window.add_magnet_from_input()

    def test_magnet_input_adds_row_into_torrents_category(self):
        self._add_magnet()
        self.assertEqual(self.window.torrents_tab.magnet_input.text(), "")
        self.assertEqual(self.table.rowCount(), 1)
        self.assertEqual(self.table.item(0, 0).text(), "Movie")
        self.assertEqual(self.table.item(0, 2).text(), "Downloading 50.0%")
        self.assertEqual(self.table.item(0, 3).text(), "00:00:02")
        save_path = self.window.torrent_engine.calls[0][1]
        self.assertTrue(save_path.endswith("Torrents"))
        self.assertIs(self.window.tabs.currentWidget(), self.window.torrents_tab)

    def test_duplicates_and_errors_do_not_add_rows(self):
        self._add_magnet()
        with patch("udm.ui.window_torrents.QMessageBox.information") as info:
            self._add_magnet()
        info.assert_called_once()
        with patch("udm.ui.window_torrents.QMessageBox.warning") as warning:
            self._add_magnet("magnet:?bad")
        warning.assert_called_once()
        self.assertEqual(self.window.torrents_tab.magnet_input.text(), "magnet:?bad")
        self.assertEqual(self.table.rowCount(), 1)

    def test_toolbar_actions_control_selected_torrents(self):
        self._add_magnet()
        self.window.tabs.setCurrentWidget(self.window.torrents_tab)
        self.table.selectRow(0)
        self.window.pause_selected()
        self.window.refresh_torrents()
        self.assertEqual(self.table.item(0, 2).text(), "Paused")
        self.window.resume_selected()
        self.window.refresh_torrents()
        self.assertTrue(self.table.item(0, 2).text().startswith("Downloading"))
        self.window.stop_all()
        self.assertEqual(self.window.torrent_engine.torrents["abc"], "Paused")
        self.table.selectRow(0)
        self.window.delete_selected()
        self.assertEqual(self.table.rowCount(), 0)
        self.assertEqual(self.window.torrent_engine.torrents, {})

    def test_close_saves_engine_state(self):
        self._add_magnet()
        engine = self.window.torrent_engine
        self.window.stop_torrents()
        self.assertIn(("close",), engine.calls)
        self.assertIsNone(self.window.torrent_engine)


class OpenEventTests(QtTestCase):
    def test_magnet_and_torrent_urls_are_recognized(self):
        self.assertEqual(torrent_source_from_url(QUrl(MAGNET)), MAGNET)
        self.assertEqual(
            torrent_source_from_url(QUrl.fromLocalFile("/tmp/a.torrent")), "/tmp/a.torrent"
        )
        self.assertIsNone(torrent_source_from_url(QUrl("https://example.com/a.torrent")))
        self.assertIsNone(torrent_source_from_url(QUrl.fromLocalFile("/tmp/a.zip")))


if __name__ == "__main__":
    unittest.main()
