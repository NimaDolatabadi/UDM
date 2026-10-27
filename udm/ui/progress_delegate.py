"""Paint a themed progress bar behind the download list's size text."""

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QStyle, QStyledItemDelegate

from udm.ui.download_roles import PROGRESS_ROLE

# Status column whose text selects the chunk color.
STATUS_COLUMN = 2


def chunk_color_token(status):
    """Return the theme token name for a progress chunk in ``status``."""
    if status == "Completed":
        return "status_success"
    if status == "Paused":
        return "status_warning"
    return "accent"


class ProgressDelegate(QStyledItemDelegate):
    """Draw a rounded progress track with the cell text centered on top.

    Cells without a ``PROGRESS_ROLE`` value (total size unknown) paint as
    plain text. ``theme_source`` returns the active theme so the bar follows
    live theme switches.
    """

    def __init__(self, theme_source, parent=None):
        super().__init__(parent)
        self._theme_source = theme_source

    def paint(self, painter, option, index):
        percent = index.data(PROGRESS_ROLE)
        theme = self._theme_source()
        if percent is None or theme is None:
            super().paint(painter, option, index)
            return
        # Draw the row's selection or hover background, without the text.
        style = option.widget.style() if option.widget else None
        if style is not None:
            style.drawPrimitive(
                QStyle.PrimitiveElement.PE_PanelItemViewItem,
                option,
                painter,
                option.widget,
            )
        status = index.siblingAtColumn(STATUS_COLUMN).data() or ""
        chunk = getattr(theme, chunk_color_token(status))
        track = QRectF(option.rect).adjusted(
            theme.space_xs, theme.space_xs, -theme.space_xs, -theme.space_xs
        )
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        outline = QPainterPath()
        outline.addRoundedRect(track, theme.radius_sm, theme.radius_sm)
        painter.fillPath(outline, QColor(theme.bg_sunken))
        filled = QRectF(track)
        filled.setWidth(track.width() * max(0, min(100, percent)) / 100)
        if filled.width() > 0:
            # Clip to the track so a narrow chunk keeps the track's rounding.
            painter.setClipPath(outline)
            painter.fillRect(filled, QColor(chunk))
            painter.setClipping(False)
        painter.setPen(QPen(QColor(theme.border_subtle), 1))
        painter.drawPath(outline)
        painter.setPen(QColor(theme.text_primary))
        # The percentage leads so eliding a narrow column drops the sizes first.
        text = painter.fontMetrics().elidedText(
            f"{percent}%  {index.data()}",
            Qt.TextElideMode.ElideRight,
            int(track.width()) - 2 * theme.space_xs,
        )
        painter.drawText(track, Qt.AlignmentFlag.AlignCenter, text)
        painter.restore()
