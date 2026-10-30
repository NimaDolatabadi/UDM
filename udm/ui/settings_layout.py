"""Shared layout helpers for settings pages."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFormLayout, QLabel, QSpinBox, QVBoxLayout, QWidget

from udm.ui.theme import theme_for

# Spacing scale is theme-independent.
SCALE = theme_for(None)

# Width of the label column, so fields line up across every settings page.
LABEL_WIDTH = 160


def settings_page(title):
    """Return a settings page widget and its content layout with a heading."""
    page = QWidget()
    outer = QVBoxLayout(page)
    outer.setContentsMargins(
        SCALE.space_xl, SCALE.space_lg, SCALE.space_xl, SCALE.space_lg
    )
    outer.setSpacing(SCALE.space_md)
    heading = QLabel(title)
    heading.setProperty("heading", True)
    outer.addWidget(heading)
    return page, outer


def settings_form():
    """Return a form layout with left-aligned labels in a shared column.

    Only fields with an expanding width policy, such as line edits, fill the
    row; combo boxes and spin boxes keep their natural width.
    """
    form = QFormLayout()
    form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
    form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.DontWrapRows)
    form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    form.setFormAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
    form.setHorizontalSpacing(SCALE.space_md)
    form.setVerticalSpacing(SCALE.space_md)
    return form


def add_form_row(form, label, field):
    """Add ``field`` to ``form`` under a label sized to the shared column."""
    caption = QLabel(label)
    caption.setMinimumWidth(LABEL_WIDTH)
    if isinstance(field, QWidget):
        caption.setBuddy(field)
    form.addRow(caption, field)
    return caption


def spin_box(minimum, maximum, value=None):
    """Return a spin box whose value is inset like other input fields.

    The stylesheet cannot pad a spin box's internal text field, so the
    ``space_sm`` inset is applied here.
    """
    spin = QSpinBox()
    spin.setRange(minimum, maximum)
    if value is not None:
        spin.setValue(int(value))
    spin.lineEdit().setTextMargins(SCALE.space_sm, 0, 0, 0)
    return spin


def section_label(text):
    """Return a title-sized label that introduces a group of settings."""
    label = QLabel(text)
    label.setProperty("section", True)
    return label


def muted_label(text):
    """Return a word-wrapped secondary-text label."""
    label = QLabel(text)
    label.setProperty("muted", True)
    label.setWordWrap(True)
    return label
