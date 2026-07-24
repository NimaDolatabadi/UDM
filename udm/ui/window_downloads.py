"""Download queue behavior for the main window."""

import os
from urllib.parse import urlparse

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QBrush, QColor
from PyQt6.QtWidgets import (
    QInputDialog,
    QMenu,
    QTableWidgetItem,
)

from udm.constants import DEFAULT_CONFIG, SCHEDULE_COLORS
from udm.i18n import TRANSLATIONS
from udm.workers import DownloadWorker

URL_ROLE = Qt.ItemDataRole.UserRole + 2
PATH_ROLE = Qt.ItemDataRole.UserRole + 3


class DownloadController:
    """Manage queue rows and their download workers."""

    def prompt_add_url(self):
        """Prompt for a URL and add it to the active download queue."""
        url, accepted = QInputDialog.getText(self, "Add URL", "Enter URL:")
        if accepted and url:
            self.add_to_downloads(url)

    def add_to_downloads(self, url, start_paused=False, schedule_idx=None):
        """Create a queue row and optionally start its worker immediately."""
        url = url.strip()
        filename = os.path.basename(urlparse(url).path) or "downloaded_file"
        target_dir = self.config_manager.get_category_path(filename)
        save_path = os.path.join(target_dir, filename)
        row = self.downloads_tab.table.rowCount()
        self.downloads_tab.table.insertRow(row)
        download_id = f"dl_{os.urandom(6).hex()}"

        name = QTableWidgetItem(filename)
        name.setData(Qt.ItemDataRole.UserRole, download_id)
        name.setData(URL_ROLE, url)
        name.setData(PATH_ROLE, save_path)
        if schedule_idx is not None:
            color_index = schedule_idx % len(SCHEDULE_COLORS)
            name.setBackground(QBrush(QColor(SCHEDULE_COLORS[color_index])))
            name.setData(Qt.ItemDataRole.UserRole + 1, schedule_idx)

        table = self.downloads_tab.table
        table.setItem(row, 0, name)
        table.setItem(row, 1, QTableWidgetItem("0%"))
        table.setItem(
            row,
            2,
            QTableWidgetItem("Paused" if start_paused else "Downloading"),
        )
        table.setItem(row, 5, QTableWidgetItem(f"Saved to: {target_dir}"))
        if not start_paused:
            self.start_worker(download_id, url, save_path)

    def start_worker(self, download_id, url, save_path):
        """Create, connect, retain, and start one download worker."""
        segments = int(self.config_manager.config.get("segments", 8))
        proxy = self.config_manager.config.get("proxy", "").strip() or None
        worker = DownloadWorker(
            download_id,
            url,
            save_path,
            segments=segments,
            proxy=proxy,
        )
        worker.progress.connect(self.on_worker_progress)
        worker.completed.connect(self.on_worker_completed)
        self.active_workers[download_id] = worker
        worker.start()

    def on_worker_progress(self, download_id, percentage, speed, status):
        """Apply a worker progress signal to its current table row."""
        row = self.find_download_row(download_id)
        if row is None:
            return
        table = self.downloads_tab.table
        table.setItem(row, 1, QTableWidgetItem(f"{percentage}%"))
        table.setItem(row, 2, QTableWidgetItem(status))
        table.setItem(row, 4, QTableWidgetItem(speed))

    def on_worker_completed(self, download_id, success, message):
        """Finalize a queue row and release its completed worker."""
        row = self.find_download_row(download_id)
        if row is not None:
            status = "Completed" if success else f"Failed: {message}"
            self.downloads_tab.table.setItem(row, 2, QTableWidgetItem(status))
            if success and self.config_manager.config.get(
                "sound_on_complete",
                False,
            ):
                self._notify_download_complete(row)
        self.active_workers.pop(download_id, None)

    def find_download_row(self, download_id):
        """Return the current row for an identifier, or None if it was removed."""
        table = self.downloads_tab.table
        # Rows can move when earlier downloads are deleted, so worker callbacks
        # resolve the identifier at signal time instead of retaining row indexes.
        for row in range(table.rowCount()):
            item = table.item(row, 0)
            if item and item.data(Qt.ItemDataRole.UserRole) == download_id:
                return row
        return None

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
            worker = self.active_workers.get(download_id)
            if worker:
                worker.pause()
            table.setItem(row, 2, QTableWidgetItem("Paused"))

    def resume_selected(self):
        """Resume workers or start queue entries that were initially paused."""
        for download_id, row, table in self.get_selected_rows_and_ids():
            worker = self.active_workers.get(download_id)
            if worker:
                worker.resume()
            elif table is self.downloads_tab.table:
                # A row added as paused has no worker yet; its URL and path roles
                # provide everything needed to start it on the first Resume.
                item = table.item(row, 0)
                self.start_worker(
                    download_id,
                    item.data(URL_ROLE),
                    item.data(PATH_ROLE),
                )
            table.setItem(row, 2, QTableWidgetItem("Downloading"))

    def stop_all(self):
        """Pause every active download worker."""
        for download_id, worker in list(self.active_workers.items()):
            worker.pause()
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
            worker = self.active_workers.pop(download_id, None)
            if worker:
                worker.cancel()
            table.removeRow(row)

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
                table.removeRow(row)

    def show_download_context_menu(self, position):
        """Show schedule assignments for the selected download rows."""
        menu = QMenu(self)
        language = self.config_manager.config.get("language", "English")
        schedule_menu = menu.addMenu(
            TRANSLATIONS.get(language, TRANSLATIONS["English"])["ctx_sched"]
        )
        schedules = self.config_manager.config.get(
            "schedules",
            DEFAULT_CONFIG["schedules"],
        )
        for index, schedule in enumerate(schedules):
            label = (
                f"{schedule['name']} ({schedule.get('start_time', '00:00')} - "
                f"{schedule.get('end_time', '06:00')})"
            )
            action = QAction(label, self)
            action.triggered.connect(
                lambda checked=False, value=index: self.assign_schedule(value)
            )
            schedule_menu.addAction(action)
        menu.exec(self.downloads_tab.table.viewport().mapToGlobal(position))

    def assign_schedule(self, schedule_index):
        """Associate selected rows with a color-coded schedule index."""
        for _, row, table in self.get_selected_rows_and_ids():
            item = table.item(row, 0)
            color = SCHEDULE_COLORS[schedule_index % len(SCHEDULE_COLORS)]
            item.setBackground(QBrush(QColor(color)))
            item.setData(Qt.ItemDataRole.UserRole + 1, schedule_index)
