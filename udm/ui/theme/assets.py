"""On-disk theme assets referenced from Qt Style Sheets.

Some QSS properties (notably ``QCheckBox::indicator`` images) can only point at a
file path, not an inline image. This module renders the small glyphs those rules
need into a cache directory and returns paths suitable for ``url(...)``. Files are
keyed by glyph and color so each theme reuses its cached asset.
"""

import tempfile
from pathlib import Path

from udm.ui.theme.glyphs import render_glyph

_CACHE_DIR = Path(tempfile.gettempdir()) / "udm_theme_assets"


def _asset_path(name, color, size):
    safe_color = color.lstrip("#")
    return _CACHE_DIR / f"{name}_{safe_color}_{size}.png"


def glyph_asset_url(name, color, size=16):
    """Render glyph ``name`` in ``color`` to a cached PNG and return its URL path.

    The returned string uses forward slashes so it can be dropped directly into a
    QSS ``url(...)`` value on any platform. Returns an empty string if rendering
    fails, letting callers omit the image rule gracefully.
    """
    path = _asset_path(name, color, size)
    if not path.exists():
        icon = render_glyph(name, color, size)
        pixmap = icon.pixmap(size, size)
        if pixmap.isNull():
            return ""
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        # Draw at the device pixel ratio Qt already baked into the icon so the
        # saved asset stays crisp on high-DPI displays.
        if not pixmap.save(str(path), "PNG"):
            return ""
    return path.as_posix()
