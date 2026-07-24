"""Dialog for editing schedule date, time, and recurrence records."""

from PyQt6.QtCore import QDate, Qt, QTime
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from udm.constants import RECURRENCE_OPTIONS, SCHEDULE_COLORS


def new_schedule():
    """Return a new schedule record with a one-week date range."""
    today = QDate.currentDate()
    return {
        "name": "New Schedule",
        "active": True,
        "max_dl": 2,
        "start_time": "08:00",
        "end_time": "17:00",
        "start_date": today.toString("yyyy-MM-dd"),
        "end_date": today.addDays(7).toString("yyyy-MM-dd"),
        "recurrence": "Every Day",
        "is_default": False,
    }


class SchedulerDialog(QDialog):
    """Edit schedule records without persisting them directly."""

    def __init__(self, schedules, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Download Scheduler Management")
        self.schedule_rows = []

        layout = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.container = QWidget()
        self.rows_layout = QVBoxLayout(self.container)
        self.rows_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(self.container)
        layout.addWidget(scroll)

        for schedule in schedules:
            self.add_schedule_row(schedule)

        add_button = QPushButton("Add Schedule")
        add_button.clicked.connect(lambda: self.add_schedule_row(new_schedule()))
        layout.addWidget(add_button)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.resize(820, 320)

    def add_schedule_row(self, schedule):
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)
        index = len(self.schedule_rows)
        color = schedule.get(
            "color",
            SCHEDULE_COLORS[index % len(SCHEDULE_COLORS)],
        )

        color_label = QLabel("  ")
        color_label.setStyleSheet(
            f"background-color: {color}; border-radius: 4px;"
        )
        color_label.setFixedSize(20, 20)
        active = QCheckBox("Enable")
        active.setChecked(schedule.get("active", False))
        name = QLineEdit(schedule.get("name", "New Schedule"))
        name.setMinimumWidth(180)
        is_default = schedule.get("is_default", False)
        name.setReadOnly(is_default)

        maximum = QSpinBox()
        maximum.setRange(1, 20)
        maximum.setValue(schedule.get("max_dl", 2))
        start_date = self._date_edit(schedule.get("start_date"), QDate.currentDate())
        end_date = self._date_edit(
            schedule.get("end_date"),
            QDate.currentDate().addDays(7),
        )
        start_time = self._time_edit(schedule.get("start_time"), QTime(0, 0))
        end_time = self._time_edit(schedule.get("end_time"), QTime(6, 0))
        recurrence = QComboBox()
        recurrence.addItems(RECURRENCE_OPTIONS)
        selected = schedule.get("recurrence", RECURRENCE_OPTIONS[0])
        recurrence.setCurrentText(
            selected if selected in RECURRENCE_OPTIONS else RECURRENCE_OPTIONS[0]
        )

        for widget in (
            color_label,
            active,
            name,
            QLabel("Max:"),
            maximum,
            QLabel("From:"),
            start_date,
            start_time,
            QLabel("To:"),
            end_date,
            end_time,
            recurrence,
        ):
            row_layout.addWidget(widget)

        delete_button = QPushButton("Delete")
        delete_button.setEnabled(not is_default)
        delete_button.clicked.connect(lambda: self.remove_schedule_row(row_widget))
        row_layout.addWidget(delete_button)
        self.rows_layout.addWidget(row_widget)
        self.schedule_rows.append(
            {
                "widget": row_widget,
                "active": active,
                "name": name,
                "max_dl": maximum,
                "start_date": start_date,
                "end_date": end_date,
                "start_time": start_time,
                "end_time": end_time,
                "recurrence": recurrence,
                "is_default": is_default,
                "color": color,
            }
        )

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

    def remove_schedule_row(self, row_widget):
        for row in self.schedule_rows:
            if row["widget"] is row_widget and not row["is_default"]:
                self.schedule_rows.remove(row)
                row_widget.deleteLater()
                return

    def get_updated_schedules(self):
        return [
            {
                "name": row["name"].text().strip(),
                "active": row["active"].isChecked(),
                "max_dl": row["max_dl"].value(),
                "start_date": row["start_date"].date().toString("yyyy-MM-dd"),
                "end_date": row["end_date"].date().toString("yyyy-MM-dd"),
                "start_time": row["start_time"].time().toString("HH:mm"),
                "end_time": row["end_time"].time().toString("HH:mm"),
                "recurrence": row["recurrence"].currentText(),
                "color": row["color"],
                "is_default": row["is_default"],
            }
            for row in self.schedule_rows
        ]
