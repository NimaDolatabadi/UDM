"""Build a Qt Style Sheet from a :class:`~udm.ui.theme.tokens.Theme`.

All component rules reference theme token values rather than literal colors or
sizes, so every theme reuses one set of rules. Rules are split into a control
fragment and a chrome fragment; this module joins them. This is the only place
raw QSS lives; widgets must not set inline styles.
"""

from udm.ui.theme.qss_chrome import chrome_qss
from udm.ui.theme.qss_controls import controls_qss
from udm.ui.theme.tokens import Theme


def build_stylesheet(theme: Theme, checkmark_url: str = "") -> str:
    """Return the complete application stylesheet for ``theme``.

    ``checkmark_url`` is an optional file path to a rendered checkmark image used
    for the checked checkbox indicator; when empty the indicator still fills with
    the accent color so the control remains usable.
    """
    checkmark_rule = f"image: url({checkmark_url});" if checkmark_url else ""
    return controls_qss(theme) + chrome_qss(theme, checkmark_rule)
