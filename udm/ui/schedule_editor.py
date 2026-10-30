"""Modal editor for a single schedule's dates, times, and recurrence.

The Scheduler window keeps only enable, edit, and delete controls per schedule;
the detailed fields live here so neither view feels cramped.
"""

from PyQt6.QtCore import QDate, QTime
from PyQt6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from udm.constants import RECURRENCE_OPTIONS
from udm.ui.settings_layout import spin_box
from udm.ui.theme import theme_for

# Spacing scale is theme-independent.
_SCALE = theme_for(None)


class ScheduleEditorDialog(QDialog):
    """Edit one schedule record in a roomy standalone modal."""

    def __init__(self, schedule, parent=None):
        super().__init__(parent)
        self.schedule = schedule
        self.is_default = schedule.get("is_default", False)
        self.setWindowTitle("Edit Schedule")
        self.resize(480, 320)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            _SCALE.space_lg, _SCALE.space_lg, _SCALE.space_lg, _SCALE.space_lg
        )
        layout.setSpacing(_SCALE.space_md)
        heading = QLabel("Edit Schedule")
        heading.setProperty("heading", True)
        layout.addWidget(heading)

        form = QFormLayout()
        form.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow
        )
        form.setHorizontalSpacing(_SCALE.space_md)
        form.setVerticalSpacing(_SCALE.space_md)

        self.name = QLineEdit(schedule.get("name", "New Schedule"))
        self.name.setReadOnly(self.is_default)
        form.addRow("Name:", self.name)

        self.start_date = self._date_edit(
            schedule.get("start_date"), QDate.currentDate()
        )
        self.start_time = self._time_edit(schedule.get("start_time"), QTime(0, 0))
        self.end_date = self._date_edit(
            schedule.get("end_date"), QDate.currentDate().addDays(7)
        )
        self.end_time = self._time_edit(schedule.get("end_time"), QTime(6, 0))
        form.addRow("From:", self._pair(self.start_date, self.start_time))
        form.addRow("To:", self._pair(self.end_date, self.end_time))

        self.recurrence = QComboBox()
        self.recurrence.addItems(RECURRENCE_OPTIONS)
        selected = schedule.get("recurrence", RECURRENCE_OPTIONS[0])
        self.recurrence.setCurrentText(
            selected if selected in RECURRENCE_OPTIONS else RECURRENCE_OPTIONS[0]
        )
        form.addRow("Repeat:", self.recurrence)

        self.maximum = spin_box(1, 20, schedule.get("max_dl", 2))
        if self.is_default:
            # The default queue's limit is the global Options > Downloads value.
            note = QLabel("Set by Simultaneous downloads in Options > Downloads")
            note.setProperty("muted", True)
            form.addRow("Max downloads:", note)
            self.maximum.hide()
        else:
            form.addRow("Max downloads:", self.maximum)

        layout.addLayout(form)
        layout.addStretch(1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @staticmethod
    def _pair(first, second):
        """Return a widget placing two editors side by side in equal columns."""
        container = QWidget()
        row = QHBoxLayout(container)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(_SCALE.space_sm)
        row.addWidget(first, 1)
        row.addWidget(second, 1)
        return container

    @staticmethod
    def _date_edit(value, fallback):
        parsed = QDate.fromString(value or "", "yyyy-MM-dd")
        editor = QDateEdit(parsed if parsed.isValid() else fallback)
        editor.setCalendarPopup(True)
        return editor

    @staticmethod
    def _time_edit(value, fallback):
        parsed = QTime.fromString(value or "", "HH:mm")
        return QTimeEdit(parsed if parsed.isValid() else fallback)

    def get_values(self):
        """Return the schedule record updated with the editor's field values."""
        updated = dict(self.schedule)
        updated.update(
            {
                "name": self.name.text().strip(),
                "start_date": self.start_date.date().toString("yyyy-MM-dd"),
                "end_date": self.end_date.date().toString("yyyy-MM-dd"),
                "start_time": self.start_time.time().toString("HH:mm"),
                "end_time": self.end_time.time().toString("HH:mm"),
                "recurrence": self.recurrence.currentText(),
                "max_dl": self.maximum.value(),
            }
        )
        return updated
