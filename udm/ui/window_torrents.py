"""Torrents tab controller: add magnets and files, show progress, persist."""

import logging
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QFileDialog, QMessageBox, QSystemTrayIcon, QTableWidgetItem

from udm import paths
from udm.torrent.engine import RESUME_SUFFIX, TorrentEngine, TorrentError, is_magnet
from udm.torrent.status import COMPLETED, PAUSED
from udm.workers.formatting import format_duration, format_rate

REFRESH_INTERVAL_MS = 1000
# States that show a percentage next to the label.
_ACTIVE_STATES = {"Downloading", "Checking", "Allocating"}


def torrent_state_dir():
    """Return the directory holding torrent resume files."""
    return paths.data_dir() / "torrents"


class TorrentController:
    """Own the torrent engine and mirror its torrents in the Torrents tab.

    The engine is created at startup only when saved torrents exist, and
    otherwise on the first add, so UDM opens no peer ports until needed.
    ``torrent_engine_factory`` may be replaced in tests.
    """

    torrent_engine_factory = None

    def start_torrents(self):
        """Restore saved torrents, if any, and begin refreshing the table."""
        state_dir = torrent_state_dir()
        if any(state_dir.glob(f"*{RESUME_SUFFIX}")) and self._torrent_engine(quiet=True):
            for torrent_id in self.torrent_engine.restore():
                self._torrent_row(torrent_id)
            self.refresh_torrents()

    def stop_torrents(self):
        """Save torrent state and close the session."""
        if self.torrent_timer is not None:
            self.torrent_timer.stop()
        if self.torrent_engine is not None:
            self.torrent_engine.close()
            self.torrent_engine = None

    def add_magnet_from_input(self):
        """Add the magnet link typed into the Torrents tab."""
        field = self.torrents_tab.magnet_input
        if self.add_torrent_source(field.text()):
            field.clear()

    def choose_torrent_file(self):
        """Ask for ``.torrent`` files and add each one."""
        files, _ = QFileDialog.getOpenFileNames(
            self, "Open Torrent", str(Path.home() / "Downloads"), "Torrent files (*.torrent)"
        )
        for path in files:
            self.add_torrent_source(path)

    def add_torrent_source(self, source):
        """Add a magnet link or ``.torrent`` path; return whether it was accepted."""
        source = str(source or "").strip()
        if not source:
            return False
        engine = self._torrent_engine()
        if engine is None:
            return False
        save_path = self.config_manager.get_category_path("download.torrent")
        try:
            if is_magnet(source):
                torrent_id, added = engine.add_magnet(source, save_path)
            else:
                torrent_id, added = engine.add_torrent_file(source, save_path)
        except TorrentError as error:
            QMessageBox.warning(self, "Torrent", str(error))
            return False
        if not added:
            QMessageBox.information(self, "Torrent", "This torrent is already in the list.")
        self._torrent_row(torrent_id)
        self.tabs.setCurrentWidget(self.torrents_tab)
        self.refresh_torrents()
        return True

    def pause_torrent(self, torrent_id):
        """Pause one torrent by identifier."""
        if self.torrent_engine is not None:
            self.torrent_engine.pause(torrent_id)

    def resume_torrent(self, torrent_id):
        """Resume one torrent by identifier."""
        if self.torrent_engine is not None:
            self.torrent_engine.resume(torrent_id)

    def remove_torrent(self, torrent_id):
        """Remove a torrent from the session, keeping downloaded files."""
        if self.torrent_engine is not None:
            self.torrent_engine.remove(torrent_id)
        self.torrent_finished.discard(torrent_id)

    def pause_all_torrents(self):
        """Pause every torrent in the session."""
        if self.torrent_engine is not None:
            for torrent_id in self.torrent_engine.ids():
                self.torrent_engine.pause(torrent_id)

    def refresh_torrents(self):
        """Copy the latest engine snapshots into the Torrents table."""
        if self.torrent_engine is None:
            return
        table = self.torrents_tab.table
        for snapshot in self.torrent_engine.snapshots():
            row = self._torrent_row(snapshot.torrent_id)
            status = snapshot.status
            if status in _ACTIVE_STATES:
                status = f"{status} {snapshot.progress * 100:.1f}%"
            total = self._format_size(snapshot.total_size) if snapshot.total_size else "--"
            values = (
                snapshot.name,
                f"{self._format_size(snapshot.done_bytes)} / {total}",
                status,
                format_duration(snapshot.eta) if snapshot.status not in (COMPLETED, PAUSED) else "--",
                format_rate(snapshot.download_rate),
                f"Peers {snapshot.peers} ({snapshot.seeds} seeds), "
                f"up {format_rate(snapshot.upload_rate)}",
            )
            for column, text in enumerate(values):
                item = table.item(row, column)
                if item is None or item.text() != text:
                    item = QTableWidgetItem(text)
                    if column == 0:
                        item.setData(Qt.ItemDataRole.UserRole, snapshot.torrent_id)
                    table.setItem(row, column, item)
            self._note_torrent_completion(snapshot)

    def _note_torrent_completion(self, snapshot):
        if not snapshot.finished:
            self.torrent_finished.discard(snapshot.torrent_id)
            self.torrent_seen.add(snapshot.torrent_id)
            return
        if snapshot.torrent_id in self.torrent_finished:
            return
        self.torrent_finished.add(snapshot.torrent_id)
        # Torrents restored already complete are not announced again.
        if snapshot.torrent_id in self.torrent_seen and self.tray_icon:
            self.tray_icon.showMessage(
                "UDM Torrent Complete",
                f"Successfully finished: {snapshot.name}",
                QSystemTrayIcon.MessageIcon.Information,
                3000,
            )

    def _torrent_row(self, torrent_id):
        table = self.torrents_tab.table
        for row in range(table.rowCount()):
            item = table.item(row, 0)
            if item and item.data(Qt.ItemDataRole.UserRole) == torrent_id:
                return row
        row = table.rowCount()
        table.insertRow(row)
        name = QTableWidgetItem(torrent_id)
        name.setData(Qt.ItemDataRole.UserRole, torrent_id)
        table.setItem(row, 0, name)
        table.setItem(row, 2, QTableWidgetItem("Queued"))
        return row

    def _torrent_engine(self, quiet=False):
        """Return the engine, creating it and the refresh timer on first use."""
        if self.torrent_engine is None:
            factory = self.torrent_engine_factory or TorrentEngine
            try:
                self.torrent_engine = factory(torrent_state_dir())
            except (TorrentError, OSError, RuntimeError) as error:
                logging.error("Torrent engine unavailable: %s", error)
                if not quiet:
                    QMessageBox.warning(self, "Torrent", str(error))
                return None
        if self.torrent_timer is None:
            self.torrent_timer = QTimer(self)
            self.torrent_timer.timeout.connect(self.refresh_torrents)
        if not self.torrent_timer.isActive():
            self.torrent_timer.start(REFRESH_INTERVAL_MS)
        return self.torrent_engine
