"""Hand-authored line icons rendered and recolored per theme.

Each glyph is a monochrome, stroke-based SVG on a 24x24 grid with a 2px stroke
and round caps and joins, matching the design system's line-icon style. The
stroke color is substituted at render time so a single glyph adapts to any
theme. Authored in-house, so there is no third-party icon licensing.
"""

from PyQt6.QtCore import QByteArray, QRectF, Qt
from PyQt6.QtGui import QIcon, QPainter, QPixmap
from PyQt6.QtSvg import QSvgRenderer

_COLOR_PLACEHOLDER = "{COLOR}"

# Oversampling factor for crisp rendering on high-DPI displays. The pixmap is
# painted at this multiple and flagged with a matching device pixel ratio.
_SUPERSAMPLE = 2


def _svg(body: str) -> str:
    """Wrap glyph path ``body`` in a stroke-styled SVG document."""
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
        f'fill="none" stroke="{_COLOR_PLACEHOLDER}" stroke-width="2" '
        f'stroke-linecap="round" stroke-linejoin="round">{body}</svg>'
    )


_GLYPHS = {
    # Toolbar actions.
    "add": _svg('<line x1="12" y1="5" x2="12" y2="19"/>'
                '<line x1="5" y1="12" x2="19" y2="12"/>'),
    "play": _svg('<path d="M8 5 L19 12 L8 19 Z"/>'),
    "pause": _svg('<line x1="9" y1="5" x2="9" y2="19"/>'
                  '<line x1="15" y1="5" x2="15" y2="19"/>'),
    "stop": _svg('<path d="M8.5 4 H15.5 L20 8.5 V15.5 L15.5 20 H8.5 '
                 'L4 15.5 V8.5 Z"/>'),
    "trash": _svg('<line x1="4" y1="7" x2="20" y2="7"/>'
                  '<path d="M9 7 V4 H15 V7"/>'
                  '<path d="M6 7 L7 20 H17 L18 7"/>'
                  '<line x1="10" y1="11" x2="10" y2="17"/>'
                  '<line x1="14" y1="11" x2="14" y2="17"/>'),
    "trash-check": _svg('<line x1="3" y1="7" x2="15" y2="7"/>'
                        '<path d="M7 4 H12 V7"/>'
                        '<path d="M5 7 L6 20 H13"/>'
                        '<path d="M14 14 L16.5 16.5 L21 11"/>'),
    "calendar": _svg('<rect x="3.5" y="5.5" width="17" height="15" rx="2"/>'
                     '<line x1="3.5" y1="10" x2="20.5" y2="10"/>'
                     '<line x1="8" y1="3" x2="8" y2="7"/>'
                     '<line x1="16" y1="3" x2="16" y2="7"/>'
                     '<path d="M12 13 V16 H14.5"/>'),
    "sliders": _svg('<line x1="4" y1="7" x2="20" y2="7"/>'
                    '<circle cx="9" cy="7" r="2"/>'
                    '<line x1="4" y1="12" x2="20" y2="12"/>'
                    '<circle cx="15" cy="12" r="2"/>'
                    '<line x1="4" y1="17" x2="20" y2="17"/>'
                    '<circle cx="8" cy="17" r="2"/>'),
    "globe": _svg('<circle cx="12" cy="12" r="8"/>'
                  '<line x1="4" y1="12" x2="20" y2="12"/>'
                  '<path d="M12 4 C7 8 7 16 12 20 C17 16 17 8 12 4 Z"/>'),
    # Tab glyphs.
    "download": _svg('<path d="M12 4 V14"/>'
                     '<path d="M8 11 L12 15 L16 11"/>'
                     '<path d="M5 18 H19"/>'),
    "magnet": _svg('<path d="M6 4 V11 A6 6 0 0 0 18 11 V4"/>'
                   '<line x1="6" y1="4" x2="10" y2="4"/>'
                   '<line x1="14" y1="4" x2="18" y2="4"/>'
                   '<line x1="6" y1="8" x2="10" y2="8"/>'
                   '<line x1="14" y1="8" x2="18" y2="8"/>'),
    "layers": _svg('<path d="M12 4 L20 8 L12 12 L4 8 Z"/>'
                   '<path d="M4 12 L12 16 L20 12"/>'
                   '<path d="M4 16 L12 20 L20 16"/>'),
    # Checkbox mark, drawn heavier so it reads at small indicator sizes.
    "check": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
        f'fill="none" stroke="{_COLOR_PLACEHOLDER}" stroke-width="3" '
        'stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M5 12.5 L10 17.5 L19 6.5"/></svg>'
    ),
    # Combo-box and spin-box arrows.
    "chevron-up": _svg('<path d="M6 15 L12 9 L18 15"/>'),
    "chevron-down": _svg('<path d="M6 9 L12 15 L18 9"/>'),
    # Queue-tree indicators.
    "queue": _svg('<rect x="4" y="8" width="12" height="13" rx="2"/>'
                  '<path d="M8 8 V6 A2 2 0 0 1 10 4 H18 A2 2 0 0 1 20 6 '
                  'V17 A2 2 0 0 1 18 19 H16"/>'),
    "sync": _svg('<path d="M4 12 A8 8 0 0 1 17 5.5"/>'
                 '<path d="M17 3 V6 H14"/>'
                 '<path d="M20 12 A8 8 0 0 1 7 18.5"/>'
                 '<path d="M7 21 V18 H10"/>'),
}

# Map toolbar-action keys (shared with retranslate labels) to glyph names.
ACTION_GLYPHS = {
    "add_url": "add",
    "resume": "play",
    "stop": "pause",
    "stop_all": "stop",
    "delete": "trash",
    "del_comp": "trash-check",
    "scheduler": "calendar",
    "options": "sliders",
    "grabber": "globe",
}

# Map tab identifiers to glyph names.
TAB_GLYPHS = {
    "downloads": "download",
    "torrents": "magnet",
    "grabber": "globe",
    "bulk": "layers",
}


def render_glyph(name: str, color: str, size: int = 20) -> QIcon:
    """Render glyph ``name`` stroked in ``color`` as a crisp ``QIcon``.

    Returns an empty icon for an unknown name so a missing glyph never raises.
    """
    template = _GLYPHS.get(name)
    if template is None:
        return QIcon()
    svg = template.replace(_COLOR_PLACEHOLDER, color)
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    scaled = size * _SUPERSAMPLE
    pixmap = QPixmap(scaled, scaled)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(painter, QRectF(0, 0, scaled, scaled))
    painter.end()
    pixmap.setDevicePixelRatio(_SUPERSAMPLE)
    return QIcon(pixmap)
