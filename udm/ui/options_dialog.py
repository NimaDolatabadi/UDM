"""Dialog for general, network, and category settings."""

from copy import deepcopy

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHeaderView,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from udm.constants import DEFAULT_CONFIG
from udm.i18n import TRANSLATIONS


class OptionsDialog(QDialog):
    """Collect application options without persisting them directly."""

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.original_config = deepcopy(config)
        self.setWindowTitle("UDM Options")
        self.resize(550, 450)
        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        tabs.addTab(self._build_general_tab(config), "General")
        tabs.addTab(self._build_network_tab(config), "Network")
        tabs.addTab(self._build_categories_tab(config), "Categories")
        layout.addWidget(tabs)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _build_general_tab(self, config):
        tab = QWidget()
        layout = QFormLayout(tab)
        self.language = QComboBox()
        self.language.setMinimumWidth(150)
        self.language.addItems(TRANSLATIONS)
        self.language.setCurrentText(config.get("language", "English"))
        self.start_with_os = self._check(
            "Open the app when system starts",
            config.get("start_with_os", False),
        )
        self.start_minimized = self._check(
            "Open as minimized",
            config.get("start_minimized", False),
        )
        self.close_to_tray = self._check(
            "Send app to tray when closing the app",
            config.get("close_to_tray", True),
        )
        self.clipboard_monitor = self._check(
            "Enable Clipboard Monitor",
            config.get("clipboard_monitor", False),
        )
        self.sound_on_complete = self._check(
            "Play sound/notification on download complete",
            config.get("sound_on_complete", False),
        )
        layout.addRow("Interface Language:", self.language)
        for checkbox in (
            self.start_with_os,
            self.start_minimized,
            self.close_to_tray,
            self.clipboard_monitor,
            self.sound_on_complete,
        ):
            layout.addRow(checkbox)
        return tab

    def _build_network_tab(self, config):
        tab = QWidget()
        layout = QFormLayout(tab)
        self.proxy = QLineEdit(config.get("proxy", ""))
        self.proxy.setPlaceholderText("http://user:password@proxy.server:port")
        self.dns = QLineEdit(config.get("dns", ""))
        self.dns.setPlaceholderText("8.8.8.8, 1.1.1.1")
        self.segments = QSpinBox()
        self.segments.setRange(1, 64)
        self.segments.setValue(int(config.get("segments", 8)))
        layout.addRow("Custom Proxy:", self.proxy)
        layout.addRow("Custom DNS:", self.dns)
        layout.addRow("Max Segments per File:", self.segments)
        return tab

    def _build_categories_tab(self, config):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        self.categories = QTableWidget(0, 2)
        self.categories.setHorizontalHeaderLabels(
            ["Category Path", "Extensions (comma separated)"]
        )
        self.categories.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        for category, extensions in config.get(
            "categories",
            DEFAULT_CONFIG["categories"],
        ).items():
            self.add_category(category, extensions)

        button_layout = QHBoxLayout()
        add_button = QPushButton("Add Category")
        add_button.clicked.connect(
            lambda: self.add_category("New Category", "ext1, ext2")
        )
        remove_button = QPushButton("Remove Selected")
        remove_button.clicked.connect(self.remove_selected_category)
        button_layout.addWidget(add_button)
        button_layout.addWidget(remove_button)
        layout.addWidget(self.categories)
        layout.addLayout(button_layout)
        return tab

    @staticmethod
    def _check(label, checked):
        checkbox = QCheckBox(label)
        checkbox.setChecked(checked)
        return checkbox

    def add_category(self, category, extensions):
        """Append an editable category and extension mapping."""
        row = self.categories.rowCount()
        self.categories.insertRow(row)
        self.categories.setItem(row, 0, QTableWidgetItem(category))
        self.categories.setItem(row, 1, QTableWidgetItem(extensions))

    def remove_selected_category(self):
        """Remove the category containing the current table selection."""
        selected = self.categories.selectedItems()
        if selected:
            self.categories.removeRow(selected[0].row())

    def get_updated_config(self):
        """Return edited settings while preserving fields this dialog does not own."""
        categories = {}
        for row in range(self.categories.rowCount()):
            category = self.categories.item(row, 0)
            extensions = self.categories.item(row, 1)
            if category and extensions and category.text().strip():
                categories[category.text().strip()] = extensions.text().strip()

        # Schedules and future settings are not rendered by this dialog. Begin
        # with the original record so accepting Options cannot discard them.
        updated = deepcopy(self.original_config)
        updated.update(
            {
                "language": self.language.currentText(),
                "start_with_os": self.start_with_os.isChecked(),
                "start_minimized": self.start_minimized.isChecked(),
                "close_to_tray": self.close_to_tray.isChecked(),
                "clipboard_monitor": self.clipboard_monitor.isChecked(),
                "sound_on_complete": self.sound_on_complete.isChecked(),
                "proxy": self.proxy.text().strip(),
                "dns": self.dns.text().strip(),
                "segments": self.segments.value(),
                "categories": categories,
            }
        )
        return updated
