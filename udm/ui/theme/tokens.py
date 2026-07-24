"""Design tokens and the theme registry for the application.

This module is intentionally free of any Qt import so the token values remain
importable from headless code paths and tests. Each theme fills the same
``Theme`` structure with concrete values; a theme never adds or removes tokens,
only changes them. See ``docs/design-system.md`` for the canonical definitions.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    """Concrete values for one theme, keyed by semantic token name.

    Colors are hex strings. Spacing, radius, and control-height values are
    integer pixels. The scale fields are shared across all themes; only the
    color roles differ, but every field is defined per theme so a theme is a
    complete, self-contained mapping.
    """

    name: str

    # Surfaces: three levels only. Do not introduce additional grays.
    bg_base: str
    bg_raised: str
    bg_sunken: str

    # Borders.
    border_subtle: str
    border_strong: str

    # Text.
    text_primary: str
    text_muted: str
    text_disabled: str

    # Accent family. Drives actions, selection, and focus.
    accent: str
    accent_hover: str
    accent_pressed: str
    accent_text: str
    # Selection background for rows and highlighted list items. Kept distinct
    # from ``accent`` so full-saturation accent is reserved for actions.
    selection_bg: str

    # Status colors. Reserved for meaning, never decoration.
    status_success: str
    status_warning: str
    status_danger: str
    status_info: str

    # Spacing scale (4-based).
    space_xs: int = 4
    space_sm: int = 8
    space_md: int = 12
    space_lg: int = 16

    # Radius scale.
    radius_sm: int = 4
    radius_md: int = 6
    radius_lg: int = 10

    # Control heights.
    control_md: int = 30

    # Scrollbar geometry.
    scrollbar_thickness: int = 10


REFINED_DARK = Theme(
    name="Refined Dark",
    bg_base="#1c1e22",
    bg_raised="#26292e",
    bg_sunken="#16181b",
    border_subtle="#2f333a",
    border_strong="#3d424b",
    text_primary="#e6e8eb",
    text_muted="#9aa2ad",
    text_disabled="#5c636e",
    accent="#2f81f7",
    accent_hover="#4c94f8",
    accent_pressed="#1f6feb",
    accent_text="#ffffff",
    selection_bg="#234876",
    status_success="#2ea043",
    status_warning="#d29922",
    status_danger="#f85149",
    status_info="#2f81f7",
)

LIGHT = Theme(
    name="Light",
    bg_base="#f6f7f9",
    bg_raised="#ffffff",
    bg_sunken="#eceef1",
    border_subtle="#e1e4e8",
    border_strong="#c9cdd3",
    text_primary="#1c1e22",
    text_muted="#5c636e",
    text_disabled="#a6acb5",
    accent="#2f81f7",
    accent_hover="#4c94f8",
    accent_pressed="#1f6feb",
    accent_text="#ffffff",
    selection_bg="#cfe1fb",
    status_success="#2ea043",
    status_warning="#d29922",
    status_danger="#f85149",
    status_info="#2f81f7",
)

# Concrete themes carry real token values. The first is the design default used
# whenever a concrete theme cannot otherwise be determined.
_THEMES = (REFINED_DARK, LIGHT)
_THEMES_BY_NAME = {theme.name: theme for theme in _THEMES}
_DEFAULT_CONCRETE = REFINED_DARK

# "System" is a selectable option, not a concrete theme: it follows the operating
# system's light or dark preference and resolves to one of the concrete themes.
SYSTEM_OPTION = "System"

# Ordered user-facing choices for the theme selector. System is first and is the
# default so the application follows the OS unless the user overrides it.
THEME_OPTIONS = [SYSTEM_OPTION, *(theme.name for theme in _THEMES)]
DEFAULT_THEME = SYSTEM_OPTION


def theme_for(name):
    """Return the concrete theme named ``name``.

    Falls back to the design default for any unknown name (including the
    ``System`` option, which is resolved by :func:`resolve_theme`) so a stale
    config value never prevents the application from starting.
    """
    return _THEMES_BY_NAME.get(name, _DEFAULT_CONCRETE)


def resolve_theme(option, dark_preferred):
    """Resolve a selectable ``option`` to a concrete theme.

    ``System`` maps to Refined Dark when ``dark_preferred`` is true and Light
    otherwise. Any other value is treated as a concrete theme name.
    """
    if option == SYSTEM_OPTION:
        return REFINED_DARK if dark_preferred else LIGHT
    return theme_for(option)
