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

from udm.ui.progress_delegate import ProgressDelegate
from udm.ui.theme import theme_for

# Spacing and radius scales are shared across themes, so a single resolved theme
# supplies the layout metrics without coupling tabs to any particular theme.
_SCALE = theme_for(None)


def _page_layout(widget):
    """Return a vertical layout with consistent page margins and spacing."""
    layout = QVBoxLayout(widget)
    layout.setContentsMargins(
        _SCALE.space_lg, _SCALE.space_lg, _SCALE.space_lg, _SCALE.space_lg
    )
    layout.setSpacing(_SCALE.space_md)
    return layout


def configured_table(columns):
    """Return a row-selecting, stretch-header table."""
    table = QTableWidget(0, columns)
    table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
    table.verticalHeader().setVisible(False)
    return table


class DownloadsTab(QWidget):
    """Download queue table with a progress bar in the size column.

    ``theme_source`` returns the active theme used to paint progress bars.
    """

    def __init__(self, theme_source=lambda: None):
        super().__init__()
        self.table = configured_table(6)
        self.table.setItemDelegateForColumn(
            1, ProgressDelegate(theme_source, self.table)
        )
        layout = _page_layout(self)
        layout.addWidget(self.table)


class TorrentsTab(QWidget):
    """Magnet and torrent-file controls with the torrent table."""

    def __init__(self):
        super().__init__()
        layout = _page_layout(self)
        controls = QHBoxLayout()
        controls.setSpacing(_SCALE.space_sm)
        self.magnet_input = QLineEdit()
        self.add_magnet_button = QPushButton()
        self.load_torrent_button = QPushButton()
        controls.addWidget(self.magnet_input, 1)
        controls.addWidget(self.add_magnet_button)
        controls.addWidget(self.load_torrent_button)
        self.table = configured_table(6)
        layout.addLayout(controls)
        layout.addWidget(self.table)


class GrabberTab(QWidget):
    """Single-page link discovery controls and results."""

    def __init__(self):
        super().__init__()
        layout = _page_layout(self)
        input_layout = QHBoxLayout()
        input_layout.setSpacing(_SCALE.space_sm)
        self.url_input = QLineEdit()
        self.start_button = QPushButton()
        input_layout.addWidget(self.url_input, 1)
        input_layout.addWidget(self.start_button)

        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(_SCALE.space_sm)
        self.filter_label = QLabel("Filter:")
        self.filter_input = QLineEdit()
        filter_layout.addWidget(self.filter_label)
        filter_layout.addWidget(self.filter_input, 1)

        actions = QHBoxLayout()
        actions.setSpacing(_SCALE.space_sm)
        self.select_all_button = QPushButton()
        self.transfer_button = QPushButton()
        actions.addWidget(self.select_all_button)
        actions.addWidget(self.transfer_button)
        actions.addStretch(1)

        self.results = configured_table(1)
        layout.addLayout(input_layout)
        layout.addLayout(filter_layout)
        layout.addLayout(actions)
        layout.addWidget(self.results)


class BulkTab(QWidget):
    """Recursive discovery controls, progress, and results."""

    def __init__(self):
        super().__init__()
        layout = _page_layout(self)
        form = QFormLayout()
        form.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow
        )
        form.setHorizontalSpacing(_SCALE.space_md)
        form.setVerticalSpacing(_SCALE.space_sm)
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://example.com/folder/")
        self.extensions_input = QLineEdit()
        self.extensions_input.setPlaceholderText(
            "zip, exe, pdf (comma separated)"
        )
        form.addRow("Base URL:", self.url_input)
        form.addRow("Extensions:", self.extensions_input)

        buttons = QHBoxLayout()
        buttons.setSpacing(_SCALE.space_sm)
        self.start_button = QPushButton("Start Bulk Recursive Download")
        self.stop_button = QPushButton("Stop")
        self.stop_button.setEnabled(False)
        buttons.addWidget(self.start_button, 1)
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
