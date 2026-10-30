"""Build a Qt Style Sheet from a :class:`~udm.ui.theme.tokens.Theme`.

All component rules reference theme token values rather than literal colors or
sizes, so every theme reuses one set of rules. Rules are split into a control
fragment and a chrome fragment; this module joins them. This is the only place
raw QSS lives; widgets must not set inline styles.
"""

from udm.ui.theme.qss_chrome import chrome_qss
from udm.ui.theme.qss_controls import controls_qss
from udm.ui.theme.tokens import Theme


def build_stylesheet(
    theme: Theme, checkmark_url: str = "", up_arrow_url: str = "",
    down_arrow_url: str = "",
) -> str:
    """Return the complete application stylesheet for ``theme``.

    The URLs are optional file paths to rendered glyphs: the checked checkbox
    mark and the combo-box and spin-box arrows. When one is empty its rule is
    omitted; controls stay usable, with an accent-filled checkbox or no arrow
    glyph. :func:`udm.ui.theme.assets.themed_stylesheet` supplies all three.
    """
    checkmark_rule = f"image: url({checkmark_url});" if checkmark_url else ""
    up_rule = f"image: url({up_arrow_url});" if up_arrow_url else ""
    down_rule = f"image: url({down_arrow_url});" if down_arrow_url else ""
    return controls_qss(theme, up_rule, down_rule) + chrome_qss(theme, checkmark_rule)
