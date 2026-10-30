"""Options page for where downloads go and how new downloads start."""

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from udm.config import default_download_dir
from udm.constants import DEFAULT_CONFIG, STREAM_QUALITY_OPTIONS
from udm.ui.settings_layout import (
    SCALE,
    add_form_row,
    muted_label,
    section_label,
    settings_form,
    settings_page,
    spin_box,
)


class DownloadsPage(QWidget):
    """Edit the download folder, transfer limits, and new-download behavior."""

    def __init__(self, config, parent=None):
        super().__init__(parent)
        page, outer = settings_page("Downloads")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(page)

        form = settings_form()
        add_form_row(form, "Save to", self._download_dir_row(config))
        self.quality = QComboBox()
        self.quality.addItems(STREAM_QUALITY_OPTIONS)
        self.quality.setCurrentText(
            config.get("stream_quality", DEFAULT_CONFIG["stream_quality"])
        )
        add_form_row(form, "Video quality", self.quality)
        outer.addLayout(form)
        outer.addWidget(muted_label(
            "Files are sorted into category folders inside this folder. A "
            "quality picked in the browser replaces the video quality default."
        ))

        outer.addWidget(section_label("Speed"))
        limits = settings_form()
        self.max_concurrent = self._spin(
            1, 20, config.get("max_concurrent", DEFAULT_CONFIG["max_concurrent"])
        )
        self.segments = self._spin(
            1, 64, config.get("segments", DEFAULT_CONFIG["segments"])
        )
        add_form_row(limits, "Simultaneous downloads", self.max_concurrent)
        add_form_row(limits, "Connections per file", self.segments)
        outer.addLayout(limits)

        outer.addWidget(section_label("New downloads"))
        self.confirm = self._check(
            "Ask where to save each new download",
            config.get("confirm_new_downloads", True),
        )
        self.autostart = self._check(
            "Start captured downloads immediately",
            config.get("capture_autostart", False),
        )
        self.autostart_hint = muted_label("")
        self.clipboard_monitor = self._check(
            "Offer to download links copied to the clipboard",
            config.get("clipboard_monitor", False),
        )
        self.sound_on_complete = self._check(
            "Show a notification when a download finishes",
            config.get("sound_on_complete", False),
        )
        for widget in (
            self.confirm,
            self.autostart,
            self.autostart_hint,
            self.clipboard_monitor,
            self.sound_on_complete,
        ):
            outer.addWidget(widget)
        outer.addStretch(1)

        self.confirm.toggled.connect(self._sync_autostart)
        self._sync_autostart(self.confirm.isChecked())

    @staticmethod
    def _check(label, checked):
        checkbox = QCheckBox(label)
        checkbox.setChecked(bool(checked))
        return checkbox

    @staticmethod
    def _spin(minimum, maximum, value):
        spin = spin_box(minimum, maximum, value)
        spin.setMinimumWidth(SCALE.control_md * 3)
        return spin

    def _sync_autostart(self, asking):
        """Disable the autostart choice while the save prompt decides instead."""
        self.autostart.setEnabled(not asking)
        if asking:
            self.autostart_hint.setText(
                "The prompt offers Start Now and Download Later for each "
                "download, so links from the browser wait for your choice."
            )
        else:
            self.autostart_hint.setText(
                "Links from the browser join the download list without a "
                "prompt. They wait paused unless they start immediately."
            )

    def _download_dir_row(self, config):
        """Return a folder field with a Browse button; empty means Downloads."""
        self.download_dir = QLineEdit(config.get("download_dir", ""))
        self.download_dir.setPlaceholderText(str(default_download_dir()))
        browse = QPushButton("Browse...")
        browse.setAutoDefault(False)
        browse.clicked.connect(self.choose_download_dir)
        row = QHBoxLayout()
        row.setSpacing(SCALE.space_sm)
        row.addWidget(self.download_dir, 1)
        row.addWidget(browse)
        return row

    def choose_download_dir(self):
        """Let the user pick the folder that holds the category folders."""
        start = self.download_dir.text().strip() or str(default_download_dir())
        chosen = QFileDialog.getExistingDirectory(self, "Download Folder", start)
        if chosen:
            self.download_dir.setText(chosen)

    def values(self):
        """Return the settings owned by this page."""
        return {
            "download_dir": self.download_dir.text().strip(),
            "stream_quality": self.quality.currentText(),
            "max_concurrent": self.max_concurrent.value(),
            "segments": self.segments.value(),
            "confirm_new_downloads": self.confirm.isChecked(),
            "capture_autostart": self.autostart.isChecked(),
            "clipboard_monitor": self.clipboard_monitor.isChecked(),
            "sound_on_complete": self.sound_on_complete.isChecked(),
        }
