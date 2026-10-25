"""Shared layout helpers for settings pages."""

from PyQt6.QtWidgets import QFormLayout, QLabel, QVBoxLayout, QWidget

from udm.ui.theme import theme_for

# Spacing scale is theme-independent.
SCALE = theme_for(None)


def settings_page(title):
    """Return a settings page widget and its content layout with a heading."""
    page = QWidget()
    outer = QVBoxLayout(page)
    outer.setContentsMargins(
        SCALE.space_lg, SCALE.space_lg, SCALE.space_lg, SCALE.space_lg
    )
    outer.setSpacing(SCALE.space_md)
    heading = QLabel(title)
    heading.setProperty("heading", True)
    outer.addWidget(heading)
    return page, outer


def settings_form():
    """Return a form layout with fields that grow to fill the page width."""
    form = QFormLayout()
    form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
    form.setHorizontalSpacing(SCALE.space_md)
    form.setVerticalSpacing(SCALE.space_md)
    return form


def muted_label(text):
    """Return a word-wrapped secondary-text label."""
    label = QLabel(text)
    label.setProperty("muted", True)
    label.setWordWrap(True)
    return label
