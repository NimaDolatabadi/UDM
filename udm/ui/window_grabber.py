"""Site-grabber behavior for the main window."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMessageBox, QTableWidgetItem

from udm.workers.spiders import SpiderWorker


class GrabberController:
    """Manage one-page discovery, filtering, and queue transfer."""

    def start_grabber(self):
        """Start one-page link discovery for the entered URL."""
        url = self.grabber_tab.url_input.text().strip()
        if not url:
            return
        self.grabber_tab.results.setRowCount(0)
        self.grabber_tab.start_button.setEnabled(False)
        self.spider = SpiderWorker(url)
        self.spider.found_link.connect(self.on_spider_link)
        self.spider.completed.connect(self.on_spider_completed)
        self.spider.start()

    def on_spider_completed(self):
        """Restore the grabber controls when discovery finishes."""
        self.grabber_tab.start_button.setEnabled(True)

    def on_spider_link(self, link):
        """Append one discovered link as an unchecked result."""
        table = self.grabber_tab.results
        row = table.rowCount()
        table.insertRow(row)
        item = QTableWidgetItem(link)
        item.setFlags(
            Qt.ItemFlag.ItemIsUserCheckable
            | Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsSelectable
        )
        item.setCheckState(Qt.CheckState.Unchecked)
        table.setItem(row, 0, item)
        self.apply_grab_filter()

    def apply_grab_filter(self):
        """Hide results that do not contain the case-insensitive filter."""
        text = self.grabber_tab.filter_input.text().strip().lower()
        table = self.grabber_tab.results
        for row in range(table.rowCount()):
            item = table.item(row, 0)
            table.setRowHidden(
                row,
                bool(item and text and text not in item.text().lower()),
            )

    def grabber_select_all(self):
        """Toggle the checked state of all currently visible results."""
        table = self.grabber_tab.results
        visible_items = [
            table.item(row, 0)
            for row in range(table.rowCount())
            if not table.isRowHidden(row) and table.item(row, 0)
        ]
        all_checked = bool(visible_items) and all(
            item.checkState() == Qt.CheckState.Checked for item in visible_items
        )
        new_state = (
            Qt.CheckState.Unchecked if all_checked else Qt.CheckState.Checked
        )
        for item in visible_items:
            item.setCheckState(new_state)

    def grabber_transfer(self):
        """Transfer checked discovery results to the queue in paused state."""
        transferred = 0
        table = self.grabber_tab.results
        for row in range(table.rowCount()):
            item = table.item(row, 0)
            if item and item.checkState() == Qt.CheckState.Checked:
                self.add_to_downloads(item.text(), start_paused=True)
                item.setCheckState(Qt.CheckState.Unchecked)
                transferred += 1
        if transferred:
            QMessageBox.information(
                self,
                "Transferred",
                f"Transferred {transferred} items to the download queue (Paused).",
            )
        else:
            QMessageBox.warning(self, "Transfer Failed", "No links were selected.")
