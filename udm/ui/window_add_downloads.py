"""Add new downloads to the queue, asking where and when to save them."""

import os
from urllib.parse import urlparse

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QBrush, QColor
from PyQt6.QtWidgets import QInputDialog, QTableWidgetItem

from udm.capture import STREAM_KIND
from udm.constants import SCHEDULE_COLORS
from udm.ui.download_prompt import DownloadPromptDialog
from udm.ui.download_roles import PATH_ROLE, SCHEDULE_ROLE, URL_ROLE

# Marks rows that route their file into a category folder by name.
_CATEGORY = object()


def suggested_filename(url, request=None):
    """Return the browser's suggested name, the URL's name, or a fallback."""
    return (
        (request.filename if request else "")
        or os.path.basename(urlparse(url.strip()).path)
        or "downloaded_file"
    )


def fixed_folder_router(folder):
    """Return a router that keeps every server-reported name in ``folder``."""
    return lambda _name: folder


def is_stream(request):
    """Return whether a capture is resolved by yt-dlp rather than fetched."""
    return request is not None and request.kind == STREAM_KIND


class AddDownloadController:
    """Create queue rows for single links, captures, and batch transfers."""

    def prompt_add_url(self):
        """Prompt for a URL and offer it as a new download."""
        url, accepted = QInputDialog.getText(self, "Add URL", "Enter URL:")
        if accepted and url.strip():
            self.offer_download(url)

    def prompts_for_downloads(self):
        """Return whether new single downloads open the save prompt."""
        return self.config_manager.config.get("confirm_new_downloads", True)

    def offer_download(self, url, request=None, start_paused=False):
        """Ask where and when to save a link or capture, then queue it.

        With the prompt turned off in Options, the download is queued at once
        and ``start_paused`` decides whether it waits. Returns the opened
        dialog, or None when the download was queued directly.
        """
        url = url.strip()
        if not self.prompts_for_downloads():
            self.queue_download(url, request, start_paused)
            return None
        if is_stream(request):
            name = request.display_name()
            folder = self.config_manager.get_category_path("stream.mp4")
        else:
            name = suggested_filename(url, request)
            folder = self.config_manager.get_category_path(name)
        dialog = DownloadPromptDialog(
            url, name, folder, rename=not is_stream(request), parent=self
        )
        dialog.chosen.connect(
            lambda choice: self.queue_download(
                url,
                request,
                not choice.start_now,
                choice.folder,
                choice.filename,
            )
        )
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()
        return dialog

    def queue_download(
        self, url, request=None, start_paused=False, folder=None, filename=None
    ):
        """Add a direct download or a stream row; return its identifier."""
        if is_stream(request):
            return self.add_stream(request, start_paused=start_paused, folder=folder)
        return self.add_to_downloads(
            url,
            start_paused=start_paused,
            request=request,
            folder=folder,
            filename=filename,
        )

    def add_to_downloads(
        self,
        url,
        start_paused=False,
        schedule_idx=None,
        request=None,
        folder=None,
        filename=None,
    ):
        """Create a file-download row and queue it for the scheduler.

        ``request`` is an optional :class:`~udm.capture.CaptureRequest` whose
        browser headers and suggested filename are used for the transfer.
        ``folder`` replaces the category folder, and ``filename`` fixes the
        name so the server's name is not adopted. Returns the download
        identifier.
        """
        url = url.strip()
        if filename:
            router = None
        elif folder:
            router = fixed_folder_router(folder)
        else:
            router = _CATEGORY
        filename = filename or suggested_filename(url, request)
        target_dir = folder or self.config_manager.get_category_path(filename)
        save_path = self._unique_save_path(target_dir, filename)
        return self._insert_row(
            url,
            os.path.basename(save_path),
            save_path,
            f"Saved to: {target_dir}",
            start_paused,
            schedule_idx,
            request,
            router,
        )

    def add_stream(self, request, start_paused=False, folder=None):
        """Create a row resolved by yt-dlp for a page or stream manifest."""
        target_dir = folder or self.config_manager.get_category_path("stream.mp4")
        return self._insert_row(
            request.url,
            request.display_name(),
            target_dir,
            f"Stream to: {target_dir}",
            start_paused,
            None,
            request,
        )

    def _insert_row(
        self,
        url,
        label,
        save_path,
        description,
        start_paused,
        schedule_idx,
        request,
        router=_CATEGORY,
    ):
        table = self.downloads_tab.table
        row = table.rowCount()
        table.insertRow(row)
        download_id = f"dl_{os.urandom(6).hex()}"
        name = QTableWidgetItem(label)
        name.setData(Qt.ItemDataRole.UserRole, download_id)
        name.setData(URL_ROLE, url)
        name.setData(PATH_ROLE, save_path)
        if schedule_idx is not None:
            color_index = schedule_idx % len(SCHEDULE_COLORS)
            name.setBackground(QBrush(QColor(SCHEDULE_COLORS[color_index])))
            name.setData(SCHEDULE_ROLE, schedule_idx)
        table.setItem(row, 0, name)
        table.setItem(row, 1, QTableWidgetItem("0 B / --"))
        table.setItem(
            row, 2, QTableWidgetItem("Paused" if start_paused else "Queued")
        )
        table.setItem(row, 3, QTableWidgetItem("--"))
        table.setItem(row, 4, QTableWidgetItem("--"))
        table.setItem(row, 5, QTableWidgetItem(description))
        if request is not None:
            self.download_requests[download_id] = request
        # A None router keeps the user's exact name; the category default is
        # resolved when the worker is created.
        if router is not _CATEGORY:
            self.download_routers[download_id] = router
        self.pending_downloads[download_id] = (url, save_path)
        if start_paused:
            self.manually_paused.add(download_id)
        self.reconcile_download_queue()
        return download_id
