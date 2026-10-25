"""Plain snapshots of torrent progress for display, independent of libtorrent."""

from dataclasses import dataclass

COMPLETED = "Completed"
PAUSED = "Paused"

_STATE_LABELS = {
    "checking_files": "Checking",
    "checking_resume_data": "Checking",
    "queued_for_checking": "Checking",
    "downloading_metadata": "Fetching metadata",
    "downloading": "Downloading",
    "allocating": "Allocating",
    "finished": COMPLETED,
    "seeding": COMPLETED,
}


@dataclass(frozen=True)
class TorrentSnapshot:
    """One torrent's progress at a point in time.

    ``eta`` is seconds remaining, or ``None`` when unknown. ``status`` is the
    user-facing label; ``Completed`` and ``Paused`` match the download queue.
    """

    torrent_id: str
    name: str
    total_size: int
    done_bytes: int
    progress: float
    status: str
    download_rate: int
    upload_rate: int
    peers: int
    seeds: int
    finished: bool
    eta: int | None = None


def status_label(state, paused=False, error="", finished=False):
    """Return the label for a libtorrent state name and flags.

    Errors take precedence, then completion (a finished torrent stays
    ``Completed`` even when paused to stop seeding), then a user pause.
    """
    if error:
        return f"Failed: {error}"
    if finished:
        return COMPLETED
    if paused:
        return PAUSED
    return _STATE_LABELS.get(state, state.replace("_", " ").capitalize())


def estimate_eta(total_size, done_bytes, download_rate):
    """Return seconds until completion at the current rate, or ``None``."""
    if not total_size or download_rate <= 0:
        return None
    return max(0, int((total_size - done_bytes) / download_rate))


def snapshot_from_status(torrent_id, status, paused):
    """Build a :class:`TorrentSnapshot` from a libtorrent ``torrent_status``."""
    finished = bool(status.is_finished or status.is_seeding)
    error = status.errc.message() if status.errc.value() else ""
    total = int(status.total_wanted or 0)
    done = int(status.total_wanted_done or 0)
    rate = int(status.download_payload_rate or 0)
    return TorrentSnapshot(
        torrent_id=torrent_id,
        name=status.name or torrent_id,
        total_size=total,
        done_bytes=done,
        progress=float(status.progress or 0),
        status=status_label(status.state.name, paused, error, finished),
        download_rate=rate,
        upload_rate=int(status.upload_payload_rate or 0),
        peers=int(status.num_peers or 0),
        seeds=int(status.num_seeds or 0),
        finished=finished,
        eta=None if finished or paused else estimate_eta(total, done, rate),
    )
