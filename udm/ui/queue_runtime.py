"""Runtime admission policy for scheduled download queues."""

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtWidgets import QTableWidgetItem

from udm.constants import DEFAULT_CONFIG
from udm.filenames import unique_path
from udm.scheduling import schedule_is_open, schedule_limit
from udm.ui.download_roles import PATH_ROLE, SCHEDULE_ROLE


class QueueRuntimeController:
    """Enforce time windows and concurrency across download queue groups."""

    def setup_download_scheduler(self):
        """Start periodic enforcement of schedule windows and concurrency."""
        self.download_scheduler_timer = QTimer(self)
        self.download_scheduler_timer.timeout.connect(
            self.reconcile_download_queue
        )
        self.download_scheduler_timer.start(1000)

    def reconcile_download_queue(self, now=None):
        """Pause, resume, and admit transfers under schedule queue limits."""
        counts = {}
        for download_id, worker in list(self.active_workers.items()):
            schedule_index, schedule = self._schedule_for(download_id)
            allowed = (
                download_id not in self.manually_paused
                and self._schedule_allows(schedule_index, schedule, now)
            )
            row = self.find_download_row(download_id)
            if allowed:
                worker.resume()
                status = self.downloads_tab.table.item(row, 2) if row is not None else None
                if status is not None and status.text() == "Scheduled":
                    self._set_status(download_id, "Downloading")
                counts[schedule_index] = counts.get(schedule_index, 0) + 1
            else:
                worker.pause()
                if row is not None and download_id not in self.manually_paused:
                    self._set_status(download_id, "Scheduled")

        for download_id, (url, save_path) in list(self.pending_downloads.items()):
            if download_id in self.manually_paused:
                continue
            schedule_index, schedule = self._schedule_for(download_id)
            if not self._schedule_allows(schedule_index, schedule, now):
                self._set_status(download_id, "Scheduled")
                continue
            if counts.get(schedule_index, 0) >= self._queue_limit(
                schedule_index,
                schedule,
            ):
                self._set_status(download_id, "Queued")
                continue
            self.start_worker(download_id, url, save_path)
            counts[schedule_index] = counts.get(schedule_index, 0) + 1
            self._set_status(download_id, "Downloading")

    def _schedule_for(self, download_id):
        schedules = self.config_manager.config.get(
            "schedules",
            DEFAULT_CONFIG["schedules"],
        )
        row = self.find_download_row(download_id)
        item = self.downloads_tab.table.item(row, 0) if row is not None else None
        index = item.data(SCHEDULE_ROLE) if item else None
        if not isinstance(index, int) or not 0 <= index < len(schedules):
            index = 0
        return index, schedules[index]

    @staticmethod
    def _schedule_allows(index, schedule, now):
        # The default queue is always time-eligible. Explicit schedules add
        # their configured date, recurrence, and time-window restrictions.
        return index == 0 or schedule_is_open(schedule, now)

    def _queue_limit(self, index, schedule):
        if index == 0:
            return schedule_limit(
                {"max_dl": self.config_manager.config.get(
                    "max_concurrent",
                    DEFAULT_CONFIG["max_concurrent"],
                )}
            )
        return schedule_limit(schedule)

    def _set_status(self, download_id, status):
        row = self.find_download_row(download_id)
        if row is not None:
            self.downloads_tab.table.setItem(
                row,
                2,
                QTableWidgetItem(status),
            )

    def _unique_save_path(self, target_dir, filename):
        reserved = {
            self.downloads_tab.table.item(row, 0).data(PATH_ROLE)
            for row in range(self.downloads_tab.table.rowCount())
            if self.downloads_tab.table.item(row, 0)
        }
        return str(unique_path(target_dir, filename, reserved))

    @staticmethod
    def _format_size(byte_count):
        value = float(byte_count)
        for unit in ("B", "KB", "MB", "GB"):
            if value < 1024 or unit == "GB":
                return f"{value:.1f} {unit}"
            value /= 1024
