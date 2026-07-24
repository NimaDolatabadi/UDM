"""Design-system theming: tokens, stylesheet building, and themed icons.

Public surface for the rest of the UI. Import theme names and helpers from here
rather than reaching into submodules. See ``docs/design-system.md``.
"""

from udm.ui.theme.glyphs import ACTION_GLYPHS, TAB_GLYPHS, render_glyph
from udm.ui.theme.stylesheet import build_stylesheet
from udm.ui.theme.tokens import (
    DEFAULT_THEME,
    SYSTEM_OPTION,
    THEME_OPTIONS,
    Theme,
    resolve_theme,
    theme_for,
)


def stylesheet_for(name):
    """Return the complete stylesheet for the concrete theme named ``name``.

    Unknown names fall back to the default concrete theme via :func:`theme_for`.
    The ``System`` option is resolved by :func:`resolve_theme`, not here.
    """
    return build_stylesheet(theme_for(name))


__all__ = [
    "ACTION_GLYPHS",
    "TAB_GLYPHS",
    "DEFAULT_THEME",
    "SYSTEM_OPTION",
    "THEME_OPTIONS",
    "Theme",
    "build_stylesheet",
    "render_glyph",
    "resolve_theme",
    "stylesheet_for",
    "theme_for",
]
