"""Qt-free libtorrent session that adds, controls, and persists torrents.

Each torrent is identified by the info-hash text recorded when it was added,
which also names its resume file in the state directory. Resume files are
written whenever libtorrent produces resume data, so torrents survive both
normal exits and crashes.
"""

from collections import Counter
import logging
import os
from pathlib import Path
import time

from udm.torrent.status import snapshot_from_status

MAGNET_PREFIX = "magnet:?"
RESUME_SUFFIX = ".resume"
DEFAULT_PORT = 6881


class TorrentError(Exception):
    """A torrent could not be parsed, added, or controlled."""


def is_available():
    """Return whether the libtorrent Python bindings can be imported."""
    try:
        import libtorrent  # noqa: F401
    except ImportError:
        return False
    return True


def is_magnet(text):
    """Return whether ``text`` is a magnet URI."""
    return str(text or "").strip().lower().startswith(MAGNET_PREFIX)


def _load_libtorrent():
    try:
        import libtorrent
    except ImportError as error:
        raise TorrentError(
            "Torrent support needs the libtorrent package (pip install libtorrent)."
        ) from error
    return libtorrent


class TorrentEngine:
    """Own one libtorrent session and the torrents added to it.

    ``seed`` keeps uploading after completion; when false, finished torrents
    are paused. ``settings`` overrides libtorrent session settings, and
    ``lt_module`` replaces the libtorrent module in tests.
    """

    def __init__(
        self,
        state_dir,
        user_agent="UDM",
        seed=False,
        port=DEFAULT_PORT,
        settings=None,
        lt_module=None,
    ):
        self.lt = lt_module or _load_libtorrent()
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.seed = seed
        self._handles = {}
        # Resume-data requests per torrent whose alert has not arrived yet.
        self._pending_saves = Counter()
        category = self.lt.alert_category
        options = {
            "user_agent": user_agent,
            "listen_interfaces": f"0.0.0.0:{port},[::]:{port}",
            "alert_mask": category.error | category.status | category.storage,
            "enable_dht": True,
            "enable_lsd": True,
            "enable_upnp": True,
            "enable_natpmp": True,
        }
        options.update(settings or {})
        self.session = self.lt.session(options)

    def add_magnet(self, uri, save_path):
        """Add a magnet link; return ``(torrent_id, added)``.

        ``added`` is false when the torrent was already in the session.
        """
        if not is_magnet(uri):
            raise TorrentError("Not a magnet link.")
        try:
            params = self.lt.parse_magnet_uri(uri.strip())
        except RuntimeError as error:
            raise TorrentError(f"Invalid magnet link: {error}") from error
        return self._add(params, save_path)

    def add_torrent_file(self, path, save_path):
        """Add a ``.torrent`` file; return ``(torrent_id, added)``."""
        params = self.lt.add_torrent_params()
        try:
            params.ti = self.lt.torrent_info(str(path))
        except RuntimeError as error:
            raise TorrentError(f"Invalid torrent file: {error}") from error
        return self._add(params, save_path)

    def restore(self):
        """Re-add torrents from resume files; return their identifiers."""
        restored = []
        for resume_file in sorted(self.state_dir.glob(f"*{RESUME_SUFFIX}")):
            torrent_id = resume_file.stem
            if torrent_id in self._handles:
                continue
            try:
                params = self.lt.read_resume_data(resume_file.read_bytes())
                self._handles[torrent_id] = self._start(params)
            except (OSError, RuntimeError) as error:
                logging.warning("Skipping torrent resume file %s: %s", resume_file, error)
                continue
            restored.append(torrent_id)
        return restored

    def pause(self, torrent_id):
        """Pause one torrent; unknown identifiers are ignored."""
        handle = self._handles.get(torrent_id)
        if handle is not None and handle.is_valid():
            handle.pause()
            self._request_save(handle)

    def resume(self, torrent_id):
        """Resume one torrent; unknown identifiers are ignored."""
        handle = self._handles.get(torrent_id)
        if handle is not None and handle.is_valid():
            handle.resume()

    def remove(self, torrent_id, delete_files=False):
        """Remove a torrent and its resume file, optionally deleting its data."""
        handle = self._handles.pop(torrent_id, None)
        # A removed torrent's queued saves never complete.
        self._pending_saves.pop(torrent_id, None)
        if handle is not None and handle.is_valid():
            flags = self.lt.session.delete_files if delete_files else 0
            self.session.remove_torrent(handle, flags)
        (self.state_dir / f"{torrent_id}{RESUME_SUFFIX}").unlink(missing_ok=True)

    def ids(self):
        """Return the identifiers of every torrent in the session."""
        return list(self._handles)

    def snapshots(self):
        """Process pending alerts and return a snapshot for every torrent."""
        self._drain_alerts()
        result = []
        for torrent_id, handle in list(self._handles.items()):
            if not handle.is_valid():
                continue
            status = handle.status()
            paused = bool(status.flags & self.lt.torrent_flags.paused)
            snapshot = snapshot_from_status(torrent_id, status, paused)
            if snapshot.finished and not paused and not self.seed:
                self.pause(torrent_id)
            result.append(snapshot)
        return result

    def save_state(self, timeout=5.0):
        """Write resume data for every torrent, waiting up to ``timeout``."""
        for handle in self._handles.values():
            if handle.is_valid():
                self._request_save(handle)
        # Earlier requests (from add or pause) may still be queued; waiting for
        # all of them keeps an older save from landing last and winning.
        deadline = time.monotonic() + timeout
        while self._pending_saves.total() and time.monotonic() < deadline:
            self.session.wait_for_alert(250)
            self._drain_alerts()

    def close(self):
        """Save state and release the session."""
        self.save_state()
        self._handles.clear()
        self.session = None

    def _add(self, params, save_path):
        source = params.ti.info_hashes() if params.ti is not None else params.info_hashes
        torrent_id = str(source.get_best())
        if torrent_id in self._handles:
            return torrent_id, False
        params.save_path = str(save_path)
        # libtorrent's default flags add torrents paused for auto-management.
        params.flags &= ~self.lt.torrent_flags.paused
        try:
            handle = self._start(params)
        except RuntimeError as error:
            raise TorrentError(str(error)) from error
        self._handles[torrent_id] = handle
        # Persist immediately so a crash does not lose the new torrent.
        self._request_save(handle)
        return torrent_id, True

    def _start(self, params):
        # Auto-management would resume torrents the user paused.
        params.flags &= ~self.lt.torrent_flags.auto_managed
        return self.session.add_torrent(params)

    def _request_save(self, handle):
        handle.save_resume_data(self.lt.save_resume_flags_t.save_info_dict)
        torrent_id = self._id_of(handle)
        if torrent_id is not None:
            self._pending_saves[torrent_id] += 1

    def _id_of(self, handle):
        return next((key for key, value in self._handles.items() if value == handle), None)

    def _settle_save(self, handle):
        torrent_id = self._id_of(handle)
        if self._pending_saves.get(torrent_id, 0) > 0:
            self._pending_saves[torrent_id] -= 1

    def _drain_alerts(self):
        """Handle queued alerts; return how many resume requests finished."""
        finished = 0
        for alert in self.session.pop_alerts():
            if isinstance(alert, self.lt.save_resume_data_alert):
                self._write_resume(alert.handle, alert.params)
                self._settle_save(alert.handle)
                finished += 1
            elif isinstance(alert, self.lt.save_resume_data_failed_alert):
                self._settle_save(alert.handle)
                finished += 1
            elif isinstance(alert, (self.lt.tracker_alert, self.lt.portmap_error_alert)):
                # Unreachable trackers and failed router port mappings are
                # routine; DHT and outgoing peer connections usually suffice.
                logging.debug("Torrent: %s", alert.message())
            elif alert.category() & self.lt.alert_category.error:
                logging.warning("Torrent: %s", alert.message())
        return finished

    def _write_resume(self, handle, params):
        torrent_id = self._id_of(handle)
        if torrent_id is None:
            return
        target = self.state_dir / f"{torrent_id}{RESUME_SUFFIX}"
        temporary = target.with_suffix(".tmp")
        try:
            temporary.write_bytes(self.lt.write_resume_data_buf(params))
            os.replace(temporary, target)
        except OSError as error:
            logging.warning("Could not save torrent state %s: %s", target, error)
