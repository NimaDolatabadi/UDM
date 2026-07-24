"""Programmatically rendered queue icons."""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QBrush, QColor, QIcon, QPainter, QPen, QPixmap


def create_queue_icon(color_name, file_count, has_clock=False):
    """Create a small stacked-file queue icon."""
    pixmap = QPixmap(32, 32)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QBrush(QColor(color_name)))
    painter.setPen(QPen(Qt.GlobalColor.black, 1))

    for index in range(file_count):
        painter.drawRect(2 + index * 6, 2 + index * 6, 14, 18)

    if has_clock:
        painter.setBrush(QBrush(QColor("white")))
        painter.setPen(QPen(QColor("black"), 2))
        painter.drawEllipse(16, 16, 14, 14)
        painter.drawLine(23, 23, 23, 19)
        painter.drawLine(23, 23, 26, 23)

    painter.end()
    return QIcon(pixmap)
