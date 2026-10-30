"""Options page for the proxy and DNS settings."""

from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from udm.proxy import (
    PROXY_HTTP,
    PROXY_NONE,
    PROXY_SOCKS5,
    ProxySettings,
    build_proxy_url,
    is_supported_proxy_url,
    parse_proxy_url,
)
from udm.ui.segmented_control import SegmentedControl
from udm.ui.settings_layout import (
    SCALE,
    add_form_row,
    muted_label,
    section_label,
    settings_form,
    settings_page,
    spin_box,
)

PROXY_CHOICES = (
    (PROXY_NONE, "No proxy"),
    (PROXY_HTTP, "HTTP"),
    (PROXY_SOCKS5, "SOCKS5"),
)
_PROXY_HINTS = {
    PROXY_NONE: "Downloads connect directly.",
    PROXY_HTTP: "File and video downloads go through this HTTP proxy. "
    "Torrents connect directly.",
    PROXY_SOCKS5: "File and video downloads go through this SOCKS5 proxy, "
    "which also looks up host names. Torrents connect directly.",
}


class NetworkPage(QWidget):
    """Edit the proxy as a type plus server fields, and the DNS servers.

    The stored ``proxy`` value stays a single URL; see :mod:`udm.proxy`.
    Until the user edits a proxy field, :meth:`values` returns the stored
    URL unchanged, so a value this page cannot represent (such as SOCKS4) is
    not lost when other options are saved.
    """

    def __init__(self, config, parent=None):
        super().__init__(parent)
        page, outer = settings_page("Network")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(page)

        self._stored_proxy = (config.get("proxy") or "").strip()
        self._proxy_edited = False
        settings = parse_proxy_url(self._stored_proxy)
        self._scheme = settings.scheme
        outer.addWidget(section_label("Proxy"))
        self.proxy_kind = SegmentedControl(PROXY_CHOICES)
        kind_row = QHBoxLayout()
        kind_row.addWidget(self.proxy_kind)
        kind_row.addStretch(1)
        outer.addLayout(kind_row)
        self.proxy_hint = muted_label("")
        outer.addWidget(self.proxy_hint)
        self.proxy_details = self._build_proxy_details(settings)
        outer.addWidget(self.proxy_details)

        outer.addWidget(section_label("DNS"))
        form = settings_form()
        self.dns = QLineEdit(config.get("dns", ""))
        self.dns.setPlaceholderText("8.8.8.8, 1.1.1.1")
        add_form_row(form, "DNS servers", self.dns)
        outer.addLayout(form)
        outer.addWidget(muted_label(
            "Separate servers with commas. Leave empty to use the system's DNS."
        ))
        outer.addStretch(1)

        self.proxy_kind.changed.connect(self._show_kind)
        if is_supported_proxy_url(self._stored_proxy):
            self.proxy_kind.set_value(settings.kind)
            self._show_kind(settings.kind)
        else:
            # No segment is selected, so choosing any type is a deliberate
            # replacement of the stored value.
            self.proxy_details.hide()
            self.proxy_hint.setText(
                "Your saved proxy uses a type this page can't edit. It stays "
                "in use until you choose a type here."
            )
        # Connected after the fields are filled so loading is not an edit.
        self.proxy_kind.changed.connect(self._mark_proxy_edited)
        for field in (self.proxy_host, self.proxy_username, self.proxy_password):
            field.textEdited.connect(self._mark_proxy_edited)
        self.proxy_port.valueChanged.connect(self._mark_proxy_edited)

    def _build_proxy_details(self, settings):
        details = QWidget()
        form = settings_form()
        form.setContentsMargins(0, 0, 0, 0)
        details.setLayout(form)

        self.proxy_host = QLineEdit(settings.host)
        self.proxy_host.setPlaceholderText("proxy.example.com")
        self.proxy_host.setToolTip("A host name or address. host:port also works.")
        self.proxy_port = spin_box(0, 65535)
        # Zero shows as "Default": the scheme's standard port is used.
        self.proxy_port.setSpecialValueText("Default")
        self.proxy_port.setValue(settings.port or 0)
        self.proxy_port.setMinimumWidth(SCALE.control_md * 4)
        server_row = QHBoxLayout()
        server_row.setSpacing(SCALE.space_sm)
        server_row.addWidget(self.proxy_host, 1)
        port_label = QLabel("Port")
        port_label.setBuddy(self.proxy_port)
        server_row.addWidget(port_label)
        server_row.addWidget(self.proxy_port)
        add_form_row(form, "Server", server_row)

        self.proxy_username = QLineEdit(settings.username)
        self.proxy_username.setPlaceholderText("Optional")
        self.proxy_password = QLineEdit(settings.password)
        self.proxy_password.setPlaceholderText("Optional")
        self.proxy_password.setEchoMode(QLineEdit.EchoMode.Password)
        add_form_row(form, "Username", self.proxy_username)
        add_form_row(form, "Password", self.proxy_password)
        return details

    def _show_kind(self, kind):
        """Show the server fields only when a proxy type is selected."""
        self.proxy_details.setVisible(kind != PROXY_NONE)
        self.proxy_hint.setText(_PROXY_HINTS.get(kind, ""))

    def _mark_proxy_edited(self, *_):
        self._proxy_edited = True

    def proxy_settings(self):
        """Return the proxy currently described by the page.

        Credentials are kept exactly as typed, since spaces can be part of
        them.
        """
        return ProxySettings(
            kind=self.proxy_kind.value() or PROXY_NONE,
            host=self.proxy_host.text().strip(),
            port=self.proxy_port.value() or None,
            username=self.proxy_username.text(),
            password=self.proxy_password.text(),
            scheme=self._scheme,
        )

    def values(self):
        """Return the settings owned by this page."""
        proxy = self._stored_proxy
        if self._proxy_edited:
            proxy = build_proxy_url(self.proxy_settings())
        return {"proxy": proxy, "dns": self.dns.text().strip()}
