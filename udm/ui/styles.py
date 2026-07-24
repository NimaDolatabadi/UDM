"""Application-wide Qt style rules."""

DARK_STYLESHEET = """
QWidget {
    background-color: #2b2b2b;
    color: #e0e0e0;
    font-size: 13px;
}
QToolBar {
    background-color: #323232;
    border-bottom: 1px solid #1a1a1a;
    spacing: 8px;
    padding: 4px;
}
QToolButton {
    background-color: #3a3a3a;
    border: 1px solid #4f4f4f;
    border-radius: 5px;
    margin: 2px;
    padding: 4px;
}
QToolButton:hover {
    background-color: #4a4a4a;
    border: 1px solid #6c6c6c;
}
QToolButton:pressed {
    background-color: #252525;
    border: 1px solid #333333;
}
QTreeWidget,
QTableWidget,
QListWidget,
QTabWidget::pane {
    background-color: #1e1e1e;
    border: 1px solid #444;
}
QHeaderView::section {
    background-color: #333;
    padding: 4px;
    border: 1px solid #444;
}
QLineEdit,
QComboBox,
QSpinBox,
QTimeEdit,
QDateEdit {
    background-color: #1e1e1e;
    border: 1px solid #555;
    padding: 4px;
    color: #e0e0e0;
}
QComboBox,
QTimeEdit,
QDateEdit {
    min-width: 110px;
}
QComboBox QAbstractItemView {
    min-width: 110px;
}
QPushButton {
    background-color: #404040;
    border: 1px solid #555;
    padding: 6px;
    border-radius: 4px;
}
QPushButton:hover {
    background-color: #505050;
}
QProgressBar {
    border: 1px solid #555;
    text-align: center;
}
QProgressBar::chunk {
    background-color: #0588bc;
}
QDialog {
    background-color: #2b2b2b;
}
"""
