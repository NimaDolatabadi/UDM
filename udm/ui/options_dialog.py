"""Options dialog: a sidebar of settings pages and the merged result."""

from copy import deepcopy

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QHBoxLayout,
    QListWidget,
    QPushButton,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from udm.constants import DEFAULT_CONFIG
from udm.i18n import TRANSLATIONS
from udm.ui.options_browser_page import BrowserIntegrationPage
from udm.ui.options_downloads_page import DownloadsPage
from udm.ui.options_network_page import NetworkPage
from udm.ui.settings_layout import SCALE as _SCALE
from udm.ui.settings_layout import add_form_row, settings_form, settings_page
from udm.ui.theme import DEFAULT_THEME, THEME_OPTIONS


class OptionsDialog(QDialog):
    """Collect application options without persisting them directly."""

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.original_config = deepcopy(config)
        self.setWindowTitle("UDM Options")
        self.resize(780, 580)

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
        self.downloads_page = DownloadsPage(config)
        self.network_page = NetworkPage(config)
        self.browser_page = BrowserIntegrationPage(config)
        # Pages that own settings contribute them through values().
        self.setting_pages = (self.downloads_page, self.network_page)

        self.pages = QStackedWidget()
        for name, page in (
            ("General", self._build_general_tab(config)),
            ("Downloads", self.downloads_page),
            ("Network", self.network_page),
            ("Categories", self._build_categories_tab(config)),
            ("Browser", self.browser_page),
        ):
            self.nav.addItem(name)
            self.pages.addWidget(page)
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

    def _build_general_tab(self, config):
        page, outer = settings_page("General")
        form = settings_form()
        self.theme = QComboBox()
        self.theme.setMinimumWidth(180)
        self.theme.addItems(THEME_OPTIONS)
        self.theme.setCurrentText(config.get("theme", DEFAULT_THEME))
        self.language = QComboBox()
        self.language.setMinimumWidth(180)
        self.language.addItems(TRANSLATIONS)
        self.language.setCurrentText(config.get("language", "English"))
        add_form_row(form, "Theme", self.theme)
        add_form_row(form, "Language", self.language)
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
        for checkbox in (
            self.start_with_os,
            self.start_minimized,
            self.close_to_tray,
        ):
            outer.addWidget(checkbox)
        outer.addStretch(1)
        return page

    def _build_categories_tab(self, config):
        page, layout = settings_page("Categories")
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
                "categories": categories,
            }
        )
        for page in self.setting_pages:
            updated.update(page.values())
        return updated
