"""Focused widgets for each main application tab."""

from PyQt6.QtWidgets import (
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)


def configured_table(columns):
    """Return a row-selecting, stretch-header table."""
    table = QTableWidget(0, columns)
    table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
    return table


class DownloadsTab(QWidget):
    """Download queue table."""

    def __init__(self):
        super().__init__()
        self.table = configured_table(6)
        layout = QVBoxLayout(self)
        layout.addWidget(self.table)


class TorrentsTab(QWidget):
    """Torrent placeholder controls and table."""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        controls = QHBoxLayout()
        self.magnet_input = QLineEdit()
        self.add_magnet_button = QPushButton()
        self.load_torrent_button = QPushButton()
        controls.addWidget(self.magnet_input)
        controls.addWidget(self.add_magnet_button)
        controls.addWidget(self.load_torrent_button)
        self.table = configured_table(6)
        layout.addLayout(controls)
        layout.addWidget(self.table)


class GrabberTab(QWidget):
    """Single-page link discovery controls and results."""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        input_layout = QHBoxLayout()
        self.url_input = QLineEdit()
        self.start_button = QPushButton()
        input_layout.addWidget(self.url_input)
        input_layout.addWidget(self.start_button)

        filter_layout = QHBoxLayout()
        self.filter_label = QLabel("Filter:")
        self.filter_input = QLineEdit()
        filter_layout.addWidget(self.filter_label)
        filter_layout.addWidget(self.filter_input)

        actions = QHBoxLayout()
        self.select_all_button = QPushButton()
        self.transfer_button = QPushButton()
        actions.addWidget(self.select_all_button)
        actions.addWidget(self.transfer_button)

        self.results = configured_table(1)
        layout.addLayout(input_layout)
        layout.addLayout(filter_layout)
        layout.addLayout(actions)
        layout.addWidget(self.results)


class BulkTab(QWidget):
    """Recursive discovery controls, progress, and results."""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://example.com/folder/")
        self.extensions_input = QLineEdit()
        self.extensions_input.setPlaceholderText(
            "zip, exe, pdf (comma separated)"
        )
        form.addRow("Base URL:", self.url_input)
        form.addRow("Extensions:", self.extensions_input)

        buttons = QHBoxLayout()
        self.start_button = QPushButton("Start Bulk Recursive Download")
        self.stop_button = QPushButton("Stop")
        self.stop_button.setEnabled(False)
        buttons.addWidget(self.start_button)
        buttons.addWidget(self.stop_button)

        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.results = configured_table(1)
        self.results.setHorizontalHeaderLabels(["Discovered Recursive URLs"])
        self.transfer_button = QPushButton("Transfer All to Queue (Paused)")
        layout.addLayout(form)
        layout.addLayout(buttons)
        layout.addWidget(self.progress)
        layout.addWidget(self.results)
        layout.addWidget(self.transfer_button)
