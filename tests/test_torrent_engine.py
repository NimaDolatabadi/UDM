"""Tests for torrent status labels and the libtorrent-backed engine (offline)."""

from pathlib import Path
import tempfile
import time
import unittest

from udm.torrent.engine import TorrentEngine, TorrentError, is_available, is_magnet
from udm.torrent.status import estimate_eta, status_label

MAGNET = "magnet:?xt=urn:btih:dd8255ecdc7ca55fb0bbf81323d87062db1f6d1c&dn=Big+Buck+Bunny"
# No DHT, peer discovery, or port mapping, so the tests stay offline.
OFFLINE = {"enable_dht": False, "enable_lsd": False, "enable_upnp": False, "enable_natpmp": False}


class StatusTests(unittest.TestCase):
    def test_labels_prefer_error_then_completion_then_pause(self):
        self.assertEqual(status_label("downloading"), "Downloading")
        self.assertEqual(status_label("downloading_metadata"), "Fetching metadata")
        self.assertEqual(status_label("downloading", paused=True), "Paused")
        self.assertEqual(status_label("seeding", paused=True, finished=True), "Completed")
        self.assertEqual(status_label("downloading", error="disk full", finished=True), "Failed: disk full")

    def test_eta_requires_size_and_rate(self):
        self.assertEqual(estimate_eta(1000, 400, 100), 6)
        self.assertIsNone(estimate_eta(0, 0, 100))
        self.assertIsNone(estimate_eta(1000, 0, 0))

    def test_magnet_detection(self):
        self.assertTrue(is_magnet("  MAGNET:?xt=urn:btih:abc"))
        self.assertFalse(is_magnet("https://example.com/a.torrent"))


@unittest.skipUnless(is_available(), "libtorrent is not installed")
class EngineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.engine = self._engine()

    def tearDown(self):
        if self.engine.session is not None:
            self.engine.close()
        self.temp.cleanup()

    def _engine(self):
        return TorrentEngine(self.root / "state", port=0, settings=OFFLINE)

    def _make_torrent(self):
        import libtorrent as lt

        data = self.root / "data"
        data.mkdir()
        (data / "sample.bin").write_bytes(b"udm" * 50000)
        creator = lt.create_torrent(lt.list_files(str(data / "sample.bin")))
        lt.set_piece_hashes(creator, str(data))
        path = self.root / "sample.torrent"
        path.write_bytes(lt.bencode(creator.generate()))
        return path, data

    def _wait_for(self, predicate, timeout=10):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            snapshots = self.engine.snapshots()
            if snapshots and predicate(snapshots[0]):
                return snapshots[0]
            time.sleep(0.1)
        self.fail(f"Timed out; last snapshot {snapshots}")

    def test_invalid_sources_raise_torrent_error(self):
        with self.assertRaises(TorrentError):
            self.engine.add_magnet("https://example.com", self.root)
        bad = self.root / "bad.torrent"
        bad.write_bytes(b"not bencoded")
        with self.assertRaises(TorrentError):
            self.engine.add_torrent_file(bad, self.root)

    def test_magnet_is_added_once_and_named(self):
        torrent_id, added = self.engine.add_magnet(MAGNET, self.root / "dl")
        self.assertTrue(added)
        self.assertEqual(torrent_id, "dd8255ecdc7ca55fb0bbf81323d87062db1f6d1c")
        self.assertEqual(self.engine.add_magnet(MAGNET, self.root / "dl"), (torrent_id, False))
        snapshot = self._wait_for(lambda s: s.name == "Big Buck Bunny")
        self.assertNotEqual(snapshot.status, "Paused")

    def test_existing_data_completes_and_stops_seeding(self):
        path, data = self._make_torrent()
        torrent_id, _ = self.engine.add_torrent_file(path, data)
        snapshot = self._wait_for(lambda s: s.finished)
        self.assertEqual(snapshot.status, "Completed")
        self.assertEqual(snapshot.total_size, 150000)
        self._wait_for(lambda s: s.eta is None)
        self.assertEqual(self.engine.ids(), [torrent_id])

    def test_state_survives_restart_and_remove_forgets_it(self):
        torrent_id, _ = self.engine.add_magnet(MAGNET, self.root / "dl")
        self.engine.pause(torrent_id)
        self.engine.close()
        self.engine = self._engine()
        self.assertEqual(self.engine.restore(), [torrent_id])
        self.assertEqual(self._wait_for(lambda s: True).status, "Paused")
        self.engine.remove(torrent_id)
        self.assertEqual(self.engine.ids(), [])
        self.assertEqual(list((self.root / "state").glob("*.resume")), [])


if __name__ == "__main__":
    unittest.main()
