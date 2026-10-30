"""QSS rules for core controls: widgets, buttons, inputs, tables, tabs.

Returns a stylesheet fragment built from theme tokens. Combined with the chrome
fragment by :func:`udm.ui.theme.stylesheet.build_stylesheet`.
"""

from udm.ui.theme.tokens import Theme


def controls_qss(theme: Theme, up_arrow_rule: str = "", down_arrow_rule: str = "") -> str:
    """Return the core-control rules for ``theme``.

    The arrow rules are optional ``image: url(...)`` declarations for the
    combo-box and spin-box arrow glyphs.
    """
    # Width of the arrow column on combo and spin boxes.
    arrow_width = theme.space_xl
    return f"""
QWidget {{
    background-color: {theme.bg_base};
    color: {theme.text_primary};
    font-size: {theme.font_body}px;
}}
QWidget:disabled {{
    color: {theme.text_disabled};
}}

QToolBar {{
    background-color: {theme.bg_raised};
    border-bottom: 1px solid {theme.border_subtle};
    spacing: {theme.space_sm}px;
    padding: {theme.space_sm}px;
}}
QToolButton {{
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: {theme.radius_md}px;
    padding: {theme.space_xs}px;
    margin: 1px;
}}
QToolButton:hover {{
    background-color: {theme.bg_base};
    border: 1px solid {theme.border_subtle};
}}
QToolButton:pressed {{
    background-color: {theme.bg_sunken};
}}

QPushButton {{
    background-color: {theme.bg_raised};
    color: {theme.text_primary};
    border: 1px solid {theme.border_subtle};
    border-radius: {theme.radius_md}px;
    padding: {theme.space_xs}px {theme.space_md}px;
    min-height: {theme.control_md - 2 * theme.space_xs}px;
}}
QPushButton:hover {{
    background-color: {theme.bg_base};
    border: 1px solid {theme.border_strong};
}}
QPushButton:pressed {{
    background-color: {theme.bg_sunken};
}}
QPushButton:disabled {{
    color: {theme.text_disabled};
    border: 1px solid {theme.border_subtle};
}}
QPushButton:default {{
    background-color: {theme.accent};
    color: {theme.accent_text};
    border: 1px solid {theme.accent};
}}
QPushButton:default:hover {{
    background-color: {theme.accent_hover};
    border: 1px solid {theme.accent_hover};
}}
QPushButton:default:pressed {{
    background-color: {theme.accent_pressed};
    border: 1px solid {theme.accent_pressed};
}}

QLineEdit,
QComboBox,
QSpinBox,
QTimeEdit,
QDateEdit {{
    background-color: {theme.bg_sunken};
    color: {theme.text_primary};
    border: 1px solid {theme.border_subtle};
    border-radius: {theme.radius_sm}px;
    padding: {theme.space_xs}px {theme.space_sm}px;
    min-height: {theme.control_md - 2 * theme.space_xs}px;
    selection-background-color: {theme.accent};
    selection-color: {theme.accent_text};
}}
QLineEdit:focus,
QComboBox:focus,
QSpinBox:focus,
QTimeEdit:focus,
QDateEdit:focus {{
    border: 1px solid {theme.accent};
}}
QComboBox,
QTimeEdit,
QDateEdit {{
    min-width: 110px;
}}
QComboBox,
QSpinBox {{
    padding-right: {arrow_width}px;
}}
QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: center right;
    border: none;
    width: {arrow_width}px;
}}
QComboBox::down-arrow,
QSpinBox::down-arrow {{
    {down_arrow_rule}
    width: {theme.space_md}px;
    height: {theme.space_md}px;
}}
QSpinBox::up-arrow {{
    {up_arrow_rule}
    width: {theme.space_md}px;
    height: {theme.space_md}px;
}}
QSpinBox::up-button,
QSpinBox::down-button {{
    subcontrol-origin: border;
    width: {arrow_width}px;
    border: none;
    border-left: 1px solid {theme.border_subtle};
    background: transparent;
}}
QSpinBox::up-button {{
    subcontrol-position: top right;
    border-top-right-radius: {theme.radius_sm}px;
}}
QSpinBox::down-button {{
    subcontrol-position: bottom right;
    border-bottom-right-radius: {theme.radius_sm}px;
}}
QSpinBox::up-button:hover,
QSpinBox::down-button:hover {{
    background: {theme.bg_raised};
}}
QSpinBox::up-button:pressed,
QSpinBox::down-button:pressed {{
    background: {theme.bg_base};
}}
QComboBox QAbstractItemView {{
    background-color: {theme.bg_raised};
    border: 1px solid {theme.border_subtle};
    selection-background-color: {theme.accent};
    selection-color: {theme.accent_text};
    min-width: 110px;
    outline: none;
}}

QTreeWidget,
QTableWidget,
QListWidget,
QTabWidget::pane {{
    background-color: {theme.bg_sunken};
    border: 1px solid {theme.border_subtle};
    border-radius: {theme.radius_sm}px;
}}
QTreeWidget,
QTableWidget,
QListWidget {{
    selection-background-color: {theme.selection_bg};
    selection-color: {theme.text_primary};
    alternate-background-color: {theme.bg_base};
}}
QHeaderView::section {{
    background-color: {theme.bg_raised};
    color: {theme.text_muted};
    padding: {theme.space_sm}px;
    border: none;
    border-bottom: 1px solid {theme.border_subtle};
    border-right: 1px solid {theme.border_subtle};
}}

QTabWidget::pane {{
    top: -1px;
}}
QTabBar::tab {{
    background: transparent;
    color: {theme.text_muted};
    padding: {theme.space_sm}px {theme.space_md}px;
    border: none;
    border-bottom: 2px solid transparent;
}}
QTabBar::tab:hover {{
    color: {theme.text_primary};
}}
QTabBar::tab:selected {{
    color: {theme.accent};
    border-bottom: 2px solid {theme.accent};
}}

QProgressBar {{
    background-color: {theme.bg_sunken};
    border: 1px solid {theme.border_subtle};
    border-radius: {theme.radius_sm}px;
    text-align: center;
    color: {theme.text_primary};
}}
QProgressBar::chunk {{
    background-color: {theme.accent};
    border-radius: {theme.radius_sm}px;
}}
"""
