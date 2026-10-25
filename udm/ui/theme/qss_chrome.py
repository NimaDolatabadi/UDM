"""QSS rules for chrome: scrollbars, checkboxes, menus, dialogs, and settings.

Returns a stylesheet fragment built from theme tokens. Combined with the control
fragment by :func:`udm.ui.theme.stylesheet.build_stylesheet`.
"""

from udm.ui.theme.tokens import Theme


def chrome_qss(theme: Theme, checkmark_rule: str = "") -> str:
    """Return the chrome rules for ``theme``.

    ``checkmark_rule`` is an optional ``image: url(...)`` declaration for the
    checked checkbox indicator; empty leaves the indicator as an accent fill.
    """
    handle_radius = theme.scrollbar_thickness // 2
    return f"""
QScrollBar:vertical {{
    background: transparent;
    width: {theme.scrollbar_thickness}px;
    margin: 0px;
}}
QScrollBar::handle:vertical {{
    background: {theme.border_strong};
    border-radius: {handle_radius}px;
    min-height: 24px;
    margin: 2px;
}}
QScrollBar::handle:vertical:hover {{
    background: {theme.text_muted};
}}
QScrollBar:horizontal {{
    background: transparent;
    height: {theme.scrollbar_thickness}px;
    margin: 0px;
}}
QScrollBar::handle:horizontal {{
    background: {theme.border_strong};
    border-radius: {handle_radius}px;
    min-width: 24px;
    margin: 2px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {theme.text_muted};
}}
QScrollBar::add-line,
QScrollBar::sub-line {{
    width: 0px;
    height: 0px;
    background: none;
    border: none;
}}
QScrollBar::add-page,
QScrollBar::sub-page {{
    background: none;
}}

QCheckBox {{
    spacing: {theme.space_sm}px;
    padding: {theme.space_xs}px 0px;
}}
QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border: 1px solid {theme.border_strong};
    border-radius: {theme.radius_sm}px;
    background: {theme.bg_sunken};
}}
QCheckBox::indicator:hover {{
    border: 1px solid {theme.accent};
}}
QCheckBox::indicator:checked {{
    background: {theme.accent};
    border: 1px solid {theme.accent};
    {checkmark_rule}
}}

QSplitter::handle {{
    background: {theme.border_subtle};
}}

QMenu {{
    background-color: {theme.bg_raised};
    border: 1px solid {theme.border_subtle};
}}
QMenu::item:selected {{
    background-color: {theme.accent};
    color: {theme.accent_text};
}}

QToolTip {{
    background-color: {theme.bg_raised};
    color: {theme.text_primary};
    border: 1px solid {theme.border_subtle};
    border-radius: {theme.radius_sm}px;
    padding: {theme.space_xs}px {theme.space_sm}px;
}}

QDialog {{
    background-color: {theme.bg_base};
}}

QLabel[heading="true"] {{
    font-size: 18px;
    font-weight: 600;
    padding-bottom: {theme.space_sm}px;
}}
QLabel[muted="true"] {{
    color: {theme.text_muted};
}}

QListWidget#settingsNav {{
    background: {theme.bg_sunken};
    border: none;
    border-right: 1px solid {theme.border_subtle};
    border-radius: 0px;
    padding: {theme.space_sm}px;
    outline: none;
}}
QListWidget#settingsNav::item {{
    padding: {theme.space_sm}px {theme.space_md}px;
    border-radius: {theme.radius_md}px;
    margin-bottom: {theme.space_xs}px;
}}
QListWidget#settingsNav::item:selected {{
    background: {theme.accent};
    color: {theme.accent_text};
}}
QListWidget#settingsNav::item:hover:!selected {{
    background: {theme.bg_raised};
}}

QFrame#card {{
    background: {theme.bg_raised};
    border: 1px solid {theme.border_subtle};
    border-radius: {theme.radius_md}px;
}}

QWidget#tableCell,
QWidget#tableCell QLabel {{
    background: transparent;
}}
"""
