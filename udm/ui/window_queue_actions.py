"""Pause, resume, stop, and delete actions for download queue rows."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QTableWidgetItem

from udm.ui.download_roles import PATH_ROLE, URL_ROLE


class QueueActionsController:
    """Apply toolbar queue actions to the selected rows of the active table."""

    def get_active_table(self):
        """Return the queue table controlled by shared toolbar actions."""
        if self.tabs.currentWidget() is self.downloads_tab:
            return self.downloads_tab.table
        if self.tabs.currentWidget() is self.torrents_tab:
            return self.torrents_tab.table
        return None

    def get_selected_rows_and_ids(self):
        """Return identifiers and row locations for selected queue entries."""
        table = self.get_active_table()
        if table is None:
            return []
        return [
            (
                table.item(index.row(), 0).data(Qt.ItemDataRole.UserRole),
                index.row(),
                table,
            )
            for index in table.selectionModel().selectedRows()
            if table.item(index.row(), 0)
        ]

    def pause_selected(self):
        """Pause selected workers and update their visible queue state."""
        for download_id, row, table in self.get_selected_rows_and_ids():
            if table is self.torrents_tab.table:
                self.pause_torrent(download_id)
                continue
            worker = self.active_workers.get(download_id)
            if worker:
                worker.pause()
            self.manually_paused.add(download_id)
            table.setItem(row, 2, QTableWidgetItem("Paused"))

    def resume_selected(self):
        """Resume workers or start queue entries that were initially paused."""
        for download_id, row, table in self.get_selected_rows_and_ids():
            if table is self.torrents_tab.table:
                self.resume_torrent(download_id)
                continue
            status_item = table.item(row, 2)
            status = status_item.text() if status_item else ""
            if status == "Completed" or status.startswith("Failed"):
                continue
            worker = self.active_workers.get(download_id)
            self.manually_paused.discard(download_id)
            if worker:
                worker.resume()
            elif download_id not in self.pending_downloads:
                # A row added as paused has no worker yet; its URL and path roles
                # provide everything needed to start it on the first Resume.
                item = table.item(row, 0)
                self.pending_downloads[download_id] = (
                    item.data(URL_ROLE),
                    item.data(PATH_ROLE),
                )
            table.setItem(row, 2, QTableWidgetItem("Queued"))
        self.reconcile_download_queue()

    def stop_all(self):
        """Pause every active download worker and torrent."""
        self.pause_all_torrents()
        for download_id, worker in list(self.active_workers.items()):
            worker.pause()
            self.manually_paused.add(download_id)
            row = self.find_download_row(download_id)
            if row is not None:
                self.downloads_tab.table.setItem(
                    row,
                    2,
                    QTableWidgetItem("Paused"),
                )

    def delete_selected(self):
        """Cancel and remove all selected queue entries."""
        selections = sorted(
            self.get_selected_rows_and_ids(),
            key=lambda selection: selection[1],
            reverse=True,
        )
        # Removing bottom-up keeps remaining row indexes valid during the loop.
        for download_id, row, table in selections:
            if table is self.torrents_tab.table:
                # Torrent data stays on disk; only the transfer is removed.
                self.remove_torrent(download_id)
                table.removeRow(row)
                continue
            worker = self.active_workers.pop(download_id, None)
            if worker:
                worker.cancel()
                self.cancelling_workers[download_id] = worker
            self.pending_downloads.pop(download_id, None)
            self.download_requests.pop(download_id, None)
            self.manually_paused.discard(download_id)
            table.removeRow(row)
        self.reconcile_download_queue()

    def delete_completed(self):
        """Remove completed rows from download and torrent tables."""
        for table in (self.downloads_tab.table, self.torrents_tab.table):
            completed = [
                row
                for row in range(table.rowCount())
                if table.item(row, 2)
                and table.item(row, 2).text() == "Completed"
            ]
            for row in reversed(completed):
                if table is self.torrents_tab.table:
                    self.remove_torrent(table.item(row, 0).data(Qt.ItemDataRole.UserRole))
                table.removeRow(row)
