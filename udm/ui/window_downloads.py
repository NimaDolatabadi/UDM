"""Download workers, progress, and row updates for the main window."""

import os

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QBrush, QColor
from PyQt6.QtWidgets import QMenu, QTableWidgetItem

from udm.capture import STREAM_KIND
from udm.constants import DEFAULT_CONFIG, SCHEDULE_COLORS
from udm.i18n import TRANSLATIONS
from udm.network import create_http_session
from udm.ui.download_roles import PATH_ROLE, PROGRESS_ROLE, SCHEDULE_ROLE
from udm.ui.queue_runtime import QueueRuntimeController
from udm.ui.window_add_downloads import AddDownloadController
from udm.ui.window_queue_actions import QueueActionsController
from udm.workers.download import DownloadWorker
from udm.workers.stream import StreamWorker


class DownloadController(
    AddDownloadController, QueueActionsController, QueueRuntimeController
):
    """Manage queue rows and their download workers."""

    def start_worker(self, download_id, url, save_path):
        """Create, connect, retain, and start one download worker."""
        worker = self._create_worker(download_id, url, save_path)
        worker.progress.connect(self.on_worker_progress)
        worker.completed.connect(self.on_worker_completed)
        if isinstance(worker, StreamWorker):
            worker.renamed.connect(self.on_worker_renamed)
        else:
            worker.relocated.connect(self.on_worker_relocated)
        worker.finished.connect(
            lambda value=download_id: self._worker_finished(value)
        )
        self.active_workers[download_id] = worker
        self.pending_downloads.pop(download_id, None)
        worker.start()

    def _create_worker(self, download_id, url, save_path):
        config = self.config_manager.config
        segments = int(config.get("segments", 8))
        proxy = config.get("proxy", "").strip() or None
        request = self.download_requests.get(download_id)
        headers = request.headers() if request else None
        if request is not None and request.kind == STREAM_KIND:
            return StreamWorker(
                download_id,
                url,
                save_path,
                headers=request.stream_headers(),
                quality=request.quality
                or config.get("stream_quality", DEFAULT_CONFIG["stream_quality"]),
                proxy=proxy,
                fragments=segments,
                cookie_jar=request.cookie_jar,
                cookie_header=request.cookies,
            )
        return DownloadWorker(
            download_id,
            url,
            save_path,
            segments=segments,
            proxy=proxy,
            session=create_http_session(config.get("dns", "")),
            headers=headers,
            router=self.download_routers.get(
                download_id, self.config_manager.get_category_path
            ),
        )

    def on_worker_progress(
        self,
        download_id,
        downloaded,
        total,
        speed,
        time_left,
        status,
    ):
        """Apply a worker progress signal to its current table row."""
        row = self.find_download_row(download_id)
        if row is None:
            return
        table = self.downloads_tab.table
        size = QTableWidgetItem(
            f"{self._format_size(downloaded)} / "
            f"{self._format_size(total) if total else '--'}"
        )
        previous = table.item(row, 1)
        # Updates without a total, such as stream post-processing, keep the
        # last known percentage instead of dropping the bar.
        percent = (
            min(100, int(downloaded * 100 / total))
            if total
            else previous.data(PROGRESS_ROLE) if previous else None
        )
        size.setData(PROGRESS_ROLE, percent)
        table.setItem(row, 1, size)
        current_status = table.item(row, 2)
        if (
            download_id not in self.manually_paused
            and (not current_status or current_status.text() != "Scheduled")
        ):
            table.setItem(row, 2, QTableWidgetItem(status))
        table.setItem(row, 3, QTableWidgetItem(time_left))
        table.setItem(row, 4, QTableWidgetItem(speed))

    def on_worker_renamed(self, download_id, title):
        """Replace a stream row's placeholder label with the media title."""
        row = self.find_download_row(download_id)
        item = self.downloads_tab.table.item(row, 0) if row is not None else None
        if item is not None:
            item.setText(title)

    def on_worker_relocated(self, download_id, save_path):
        """Show the server-reported filename and its category folder."""
        row = self.find_download_row(download_id)
        if row is None:
            return
        table = self.downloads_tab.table
        item = table.item(row, 0)
        if item is not None:
            item.setText(os.path.basename(save_path))
            item.setData(PATH_ROLE, save_path)
        table.setItem(
            row, 5, QTableWidgetItem(f"Saved to: {os.path.dirname(save_path)}")
        )

    def on_worker_completed(self, download_id, success, message):
        """Finalize a queue row and release its completed worker."""
        row = self.find_download_row(download_id)
        if row is not None:
            status = "Completed" if success else f"Failed: {message}"
            self.downloads_tab.table.setItem(row, 2, QTableWidgetItem(status))
            size = self.downloads_tab.table.item(row, 1)
            if success and size is not None:
                size.setData(PROGRESS_ROLE, 100)
            if success and self.config_manager.config.get(
                "sound_on_complete",
                False,
            ):
                self._notify_download_complete(row)
        worker = self.active_workers.pop(download_id, None)
        if worker is not None:
            # A completion signal is delivered just before QThread finishes;
            # retain ownership until its finished signal reaches the UI thread.
            self.cancelling_workers[download_id] = worker
        if success:
            self.download_requests.pop(download_id, None)
            self.download_routers.pop(download_id, None)
        self.manually_paused.discard(download_id)
        self.reconcile_download_queue()

    def _worker_finished(self, download_id):
        self.active_workers.pop(download_id, None)
        self.cancelling_workers.pop(download_id, None)
        self.reconcile_download_queue()

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
            item.setData(SCHEDULE_ROLE, schedule_index)
        self.reconcile_download_queue()
