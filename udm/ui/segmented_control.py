"""Segmented control: a row of mutually exclusive choice buttons."""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QButtonGroup, QFrame, QHBoxLayout, QPushButton

from udm.ui.settings_layout import SCALE


class SegmentedControl(QFrame):
    """Pick one value from a short list of labelled options.

    ``options`` is a sequence of ``(value, label)`` pairs. Styling comes from
    the ``QFrame#segmented`` rules in the application stylesheet.
    """

    changed = pyqtSignal(str)

    def __init__(self, options, parent=None):
        super().__init__(parent)
        self.setObjectName("segmented")
        layout = QHBoxLayout(self)
        inset = SCALE.space_xs // 2
        layout.setContentsMargins(inset, inset, inset, inset)
        layout.setSpacing(inset)
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._buttons = {}
        for value, label in options:
            button = QPushButton(label)
            button.setCheckable(True)
            # Inside a dialog, auto-default buttons would take the primary
            # style and trigger on Return.
            button.setAutoDefault(False)
            self._group.addButton(button)
            self._buttons[value] = button
            layout.addWidget(button)
            button.toggled.connect(
                lambda checked, chosen=value: checked and self.changed.emit(chosen)
            )

    def value(self):
        """Return the selected value, or ``None`` before one is chosen."""
        for value, button in self._buttons.items():
            if button.isChecked():
                return value
        return None

    def set_value(self, value):
        """Select ``value``; unknown values leave the selection unchanged."""
        button = self._buttons.get(value)
        if button is not None:
            button.setChecked(True)

    def button(self, value):
        """Return the button for ``value``."""
        return self._buttons[value]
