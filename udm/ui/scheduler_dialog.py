"""Dialog listing schedules in a table with enable, edit, and delete controls.

Each row summarizes one schedule; the enable state is a checkbox under the
Enabled header, and detailed field editing opens in
:class:`~udm.ui.schedule_editor.ScheduleEditorDialog`.
"""

from copy import deepcopy

from PyQt6.QtCore import QDate, Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from udm.constants import SCHEDULE_COLORS
from udm.ui.schedule_editor import ScheduleEditorDialog
from udm.ui.theme import theme_for

# Spacing scale is theme-independent.
_SCALE = theme_for(None)


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
    """List schedules in a table and edit them without persisting directly."""

    def __init__(self, schedules, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Download Scheduler Management")
        self.schedules = [deepcopy(schedule) for schedule in schedules]
        self.schedule_rows = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            _SCALE.space_lg, _SCALE.space_lg, _SCALE.space_lg, _SCALE.space_lg
        )
        layout.setSpacing(_SCALE.space_md)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Schedule", "Enabled", "Actions"])
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setWordWrap(True)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.table)

        add_button = QPushButton("Add Schedule")
        add_button.clicked.connect(self.add_new_schedule)
        layout.addWidget(add_button)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.setMinimumWidth(560)
        self.resize(620, 440)
        self._rebuild_rows()

    def add_new_schedule(self):
        """Append a new schedule and open it for editing immediately."""
        self.schedules.append(new_schedule())
        self._rebuild_rows()
        self.edit_schedule(len(self.schedules) - 1)

    def _rebuild_rows(self):
        """Repopulate the table from the current schedule records."""
        self.schedule_rows = []
        self.table.setRowCount(0)
        for index, schedule in enumerate(self.schedules):
            self._add_row(index, schedule)
        self.table.resizeRowsToContents()

    def _add_row(self, index, schedule):
        schedule.setdefault("color", SCHEDULE_COLORS[index % len(SCHEDULE_COLORS)])
        is_default = schedule.get("is_default", False)
        self.table.insertRow(index)
        self.table.setCellWidget(index, 0, self._schedule_cell(schedule))

        active = QCheckBox()
        active.setChecked(schedule.get("active", False))
        active.toggled.connect(
            lambda checked, s=schedule: s.__setitem__("active", checked)
        )
        self.table.setCellWidget(index, 1, self._center(active))

        edit_button = QPushButton("Edit")
        edit_button.clicked.connect(lambda _, i=index: self.edit_schedule(i))
        delete_button = QPushButton("Delete")
        delete_button.setEnabled(not is_default)
        delete_button.clicked.connect(lambda _, i=index: self.delete_schedule(i))
        self.table.setCellWidget(
            index, 2, self._actions(edit_button, delete_button)
        )

        self.schedule_rows.append(
            {"schedule": schedule, "active": active, "is_default": is_default}
        )

    def _schedule_cell(self, schedule):
        cell = QWidget()
        cell.setObjectName("tableCell")
        row = QHBoxLayout(cell)
        row.setContentsMargins(
            _SCALE.space_sm, _SCALE.space_sm, _SCALE.space_sm, _SCALE.space_sm
        )
        row.setSpacing(_SCALE.space_sm)
        row.addWidget(self._color_dot(schedule["color"]))
        text = QVBoxLayout()
        text.setSpacing(2)
        name = QLabel(schedule.get("name", "Schedule"))
        summary = QLabel(self._summary(schedule))
        summary.setProperty("muted", True)
        summary.setWordWrap(True)
        text.addWidget(name)
        text.addWidget(summary)
        row.addLayout(text, 1)
        return cell

    @staticmethod
    def _center(widget):
        holder = QWidget()
        holder.setObjectName("tableCell")
        row = QHBoxLayout(holder)
        row.setContentsMargins(0, 0, 0, 0)
        row.addStretch(1)
        row.addWidget(widget)
        row.addStretch(1)
        return holder

    @staticmethod
    def _actions(*widgets):
        holder = QWidget()
        holder.setObjectName("tableCell")
        row = QHBoxLayout(holder)
        row.setContentsMargins(
            _SCALE.space_sm, _SCALE.space_xs, _SCALE.space_sm, _SCALE.space_xs
        )
        row.setSpacing(_SCALE.space_sm)
        for widget in widgets:
            row.addWidget(widget)
        return holder

    def edit_schedule(self, index):
        """Open the editor for the schedule at ``index`` and apply changes."""
        schedule = self.schedules[index]
        editor = ScheduleEditorDialog(deepcopy(schedule), self)
        if editor.exec() == QDialog.DialogCode.Accepted:
            updated = editor.get_values()
            updated["active"] = schedule.get("active", False)
            self.schedules[index] = updated
            self._rebuild_rows()

    def delete_schedule(self, index):
        """Remove a non-default schedule and rebuild the table."""
        if not self.schedules[index].get("is_default", False):
            del self.schedules[index]
            self._rebuild_rows()

    @staticmethod
    def _summary(schedule):
        """Return a one-line plain-language description of a schedule."""
        if schedule.get("is_default"):
            limit = "Global queue limit (Options > Network)"
        else:
            limit = f"Up to {schedule.get('max_dl', 2)} downloads"
        return (
            f"{schedule.get('recurrence', 'Every Day')}  ·  "
            f"{schedule.get('start_time', '00:00')}–"
            f"{schedule.get('end_time', '06:00')}  ·  "
            f"{schedule.get('start_date', '')} → "
            f"{schedule.get('end_date', '')}  ·  {limit}"
        )

    @staticmethod
    def _color_dot(color):
        """Return a small rounded swatch for the schedule's color."""
        dot = QLabel()
        dot.setFixedSize(14, 14)
        dot.setStyleSheet(f"background-color: {color}; border-radius: 7px;")
        return dot

    def get_updated_schedules(self):
        """Return the current schedule records with live enable states."""
        result = []
        for row in self.schedule_rows:
            schedule = dict(row["schedule"])
            schedule["active"] = row["active"].isChecked()
            result.append(schedule)
        return result
