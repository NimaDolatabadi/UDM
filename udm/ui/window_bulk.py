"""Recursive bulk-discovery behavior for the main window."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMessageBox, QTableWidgetItem

from udm.workers import BulkSpiderWorker


class BulkController:
    """Manage recursive discovery and queue transfer."""

    def start_bulk_download(self):
        url = self.bulk_tab.url_input.text().strip()
        extensions_text = self.bulk_tab.extensions_input.text().strip()
        if not url or not extensions_text:
            QMessageBox.warning(
                self,
                "Input Error",
                "Please provide both a Base URL and extensions.",
            )
            return
        self.bulk_tab.results.setRowCount(0)
        self.bulk_tab.progress.setValue(0)
        self.bulk_tab.start_button.setEnabled(False)
        self.bulk_tab.stop_button.setEnabled(True)
        self.bulk_spider = BulkSpiderWorker(url, extensions_text.split(","))
        self.bulk_spider.found_link.connect(self.on_bulk_link_found)
        self.bulk_spider.progress.connect(self.bulk_tab.progress.setValue)
        self.bulk_spider.completed.connect(self.on_bulk_completed)
        self.bulk_spider.start()

    def stop_bulk_download(self):
        if self.bulk_spider and self.bulk_spider.isRunning():
            self.bulk_spider.cancel()
            self.bulk_tab.stop_button.setEnabled(False)

    def on_bulk_link_found(self, link):
        table = self.bulk_tab.results
        row = table.rowCount()
        table.insertRow(row)
        item = QTableWidgetItem(link)
        item.setFlags(
            Qt.ItemFlag.ItemIsUserCheckable
            | Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsSelectable
        )
        item.setCheckState(Qt.CheckState.Checked)
        table.setItem(row, 0, item)

    def on_bulk_completed(self, total):
        self.bulk_tab.start_button.setEnabled(True)
        self.bulk_tab.stop_button.setEnabled(False)
        self.bulk_tab.progress.setValue(100)
        QMessageBox.information(
            self,
            "Bulk Scan Complete",
            f"Recursively discovered {total} matching files.",
        )

    def bulk_transfer_to_queue(self):
        transferred = 0
        table = self.bulk_tab.results
        for row in range(table.rowCount()):
            item = table.item(row, 0)
            if item and item.checkState() == Qt.CheckState.Checked:
                self.add_to_downloads(item.text(), start_paused=True)
                transferred += 1
        if transferred:
            QMessageBox.information(
                self,
                "Transferred",
                f"Transferred {transferred} recursive items to the download "
                "queue (Paused).",
            )
        else:
            QMessageBox.warning(
                self,
                "Warning",
                "No checked items found to transfer.",
            )
