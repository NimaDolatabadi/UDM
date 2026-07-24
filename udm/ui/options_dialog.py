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
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QSpinBox,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from udm.constants import DEFAULT_CONFIG
from udm.i18n import TRANSLATIONS
from udm.ui.theme import DEFAULT_THEME, THEME_OPTIONS, theme_for

# Spacing scale is theme-independent.
_SCALE = theme_for(None)


class OptionsDialog(QDialog):
    """Collect application options without persisting them directly."""

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.original_config = deepcopy(config)
        self.setWindowTitle("UDM Options")
        self.resize(760, 540)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        # Left sidebar navigation switches the stacked settings pages, replacing
        # the former compact top tab bar.
        self.nav = QListWidget()
        self.nav.setObjectName("settingsNav")
        self.nav.setFixedWidth(170)
        self.nav.addItems(["General", "Network", "Categories"])

        self.pages = QStackedWidget()
        self.pages.addWidget(self._build_general_tab(config))
        self.pages.addWidget(self._build_network_tab(config))
        self.pages.addWidget(self._build_categories_tab(config))
        self.nav.currentRowChanged.connect(self.pages.setCurrentIndex)
        self.nav.setCurrentRow(0)

        body.addWidget(self.nav)
        body.addWidget(self.pages, 1)
        layout.addLayout(body, 1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        footer = QHBoxLayout()
        footer.setContentsMargins(
            _SCALE.space_lg, _SCALE.space_md, _SCALE.space_lg, _SCALE.space_lg
        )
        footer.addWidget(buttons)
        layout.addLayout(footer)

    @staticmethod
    def _page(title):
        """Return a settings page widget and its content layout with a heading."""
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(
            _SCALE.space_lg, _SCALE.space_lg, _SCALE.space_lg, _SCALE.space_lg
        )
        outer.setSpacing(_SCALE.space_md)
        heading = QLabel(title)
        heading.setProperty("heading", True)
        outer.addWidget(heading)
        return page, outer

    def _build_general_tab(self, config):
        page, outer = self._page("General")
        form = self._form()
        self.theme = QComboBox()
        self.theme.setMinimumWidth(180)
        self.theme.addItems(THEME_OPTIONS)
        self.theme.setCurrentText(config.get("theme", DEFAULT_THEME))
        self.language = QComboBox()
        self.language.setMinimumWidth(180)
        self.language.addItems(TRANSLATIONS)
        self.language.setCurrentText(config.get("language", "English"))
        form.addRow("Theme:", self.theme)
        form.addRow("Interface Language:", self.language)
        outer.addLayout(form)

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
        for checkbox in (
            self.start_with_os,
            self.start_minimized,
            self.close_to_tray,
            self.clipboard_monitor,
            self.sound_on_complete,
        ):
            outer.addWidget(checkbox)
        outer.addStretch(1)
        return page

    def _build_network_tab(self, config):
        page, outer = self._page("Network")
        form = self._form()
        self.proxy = QLineEdit(config.get("proxy", ""))
        self.proxy.setPlaceholderText("http://user:password@proxy.server:port")
        self.dns = QLineEdit(config.get("dns", ""))
        self.dns.setPlaceholderText("8.8.8.8, 1.1.1.1")
        self.segments = QSpinBox()
        self.segments.setRange(1, 64)
        self.segments.setValue(int(config.get("segments", 8)))
        self.max_concurrent = QSpinBox()
        self.max_concurrent.setRange(1, 20)
        self.max_concurrent.setValue(
            int(config.get("max_concurrent", DEFAULT_CONFIG["max_concurrent"]))
        )
        form.addRow("Custom Proxy:", self.proxy)
        form.addRow("Custom DNS:", self.dns)
        form.addRow("Max Segments per File:", self.segments)
        form.addRow("Max Concurrent Downloads:", self.max_concurrent)
        outer.addLayout(form)
        outer.addStretch(1)
        return page

    def _build_categories_tab(self, config):
        page, layout = self._page("Categories")
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
        button_layout.setSpacing(_SCALE.space_sm)
        add_button = QPushButton("Add Category")
        add_button.clicked.connect(
            lambda: self.add_category("New Category", "ext1, ext2")
        )
        remove_button = QPushButton("Remove Selected")
        remove_button.clicked.connect(self.remove_selected_category)
        button_layout.addWidget(add_button)
        button_layout.addWidget(remove_button)
        button_layout.addStretch(1)
        layout.addWidget(self.categories, 1)
        layout.addLayout(button_layout)
        return page

    @staticmethod
    def _form():
        """Return a form layout with fields that grow to fill the page width."""
        form = QFormLayout()
        form.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow
        )
        form.setHorizontalSpacing(_SCALE.space_md)
        form.setVerticalSpacing(_SCALE.space_md)
        return form

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
                "theme": self.theme.currentText(),
                "start_with_os": self.start_with_os.isChecked(),
                "start_minimized": self.start_minimized.isChecked(),
                "close_to_tray": self.close_to_tray.isChecked(),
                "clipboard_monitor": self.clipboard_monitor.isChecked(),
                "sound_on_complete": self.sound_on_complete.isChecked(),
                "proxy": self.proxy.text().strip(),
                "dns": self.dns.text().strip(),
                "segments": self.segments.value(),
                "max_concurrent": self.max_concurrent.value(),
                "categories": categories,
            }
        )
        return updated
