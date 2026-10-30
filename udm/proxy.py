"""Proxy settings: conversion between structured fields and a proxy URL.

The configuration stores a single ``proxy`` URL, which Requests and yt-dlp
both accept directly. The Options dialog edits it as a proxy type, server,
port, and optional credentials; this module converts between the two forms.
"""

from dataclasses import dataclass
import ipaddress
from urllib.parse import quote, unquote, urlsplit

PROXY_NONE = "none"
PROXY_HTTP = "http"
PROXY_SOCKS5 = "socks5"
PROXY_KINDS = (PROXY_NONE, PROXY_HTTP, PROXY_SOCKS5)

# socks5h resolves host names on the proxy, so lookups do not leak to the
# local resolver. Requests needs PySocks for either SOCKS scheme.
_DEFAULT_SCHEME = {PROXY_HTTP: "http", PROXY_SOCKS5: "socks5h"}
_KIND_FOR_SCHEME = {
    "http": PROXY_HTTP,
    "https": PROXY_HTTP,
    "socks5": PROXY_SOCKS5,
    "socks5h": PROXY_SOCKS5,
}


@dataclass(frozen=True)
class ProxySettings:
    """One proxy configuration. ``port`` is ``None`` when not given.

    ``scheme`` keeps the exact URL scheme read from a stored value, such as
    ``https`` for a TLS proxy, so saving does not change how UDM connects.
    Empty means the default scheme for ``kind``.
    """

    kind: str = PROXY_NONE
    host: str = ""
    port: int | None = None
    username: str = ""
    password: str = ""
    scheme: str = ""


def is_supported_proxy_url(url):
    """Return whether ``url`` is empty or a proxy the Options page can edit."""
    url = (url or "").strip()
    return not url or parse_proxy_url(url).kind != PROXY_NONE


def parse_proxy_url(url):
    """Return the :class:`ProxySettings` described by ``url``.

    An empty value means no proxy. A value without a scheme is treated as an
    HTTP proxy, matching how earlier versions accepted ``host:port``. An
    unsupported scheme (such as SOCKS4) or a malformed value also yields no
    proxy; use :func:`is_supported_proxy_url` to tell these apart.
    """
    url = (url or "").strip()
    if not url:
        return ProxySettings()
    if "://" not in url:
        url = f"http://{url}"
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError:
        return ProxySettings()
    scheme = parts.scheme.lower()
    kind = _KIND_FOR_SCHEME.get(scheme)
    if kind is None or not parts.hostname:
        return ProxySettings()
    return ProxySettings(
        kind=kind,
        host=parts.hostname,
        port=port,
        username=unquote(parts.username or ""),
        password=unquote(parts.password or ""),
        scheme=scheme,
    )


def split_server(text):
    """Split a typed server into ``(host, port)``; ``port`` may be ``None``.

    Accepts a bare host, ``host:port``, a bracketed or bare IPv6 address, or a
    pasted URL. Returns ``("", None)`` when the text is not a usable host.
    """
    text = text.strip()
    if not text:
        return "", None
    if _is_ipv6(text):
        return text.strip("[]"), None
    if "://" not in text:
        text = f"//{text}"
    try:
        parts = urlsplit(text)
        port = parts.port
    except ValueError:
        return "", None
    host = parts.hostname or ""
    if "/" in host or " " in host:
        return "", None
    return host, port


def build_proxy_url(settings):
    """Return the proxy URL for ``settings``, or ``""`` for no proxy.

    Credentials are percent-encoded so characters such as ``@`` or ``:`` in a
    password survive. A colon always follows the username so an empty
    password is still sent. A proxy without a server is treated as no proxy.
    """
    if settings.kind not in _DEFAULT_SCHEME:
        return ""
    scheme = settings.scheme
    if _KIND_FOR_SCHEME.get(scheme) != settings.kind:
        scheme = _DEFAULT_SCHEME[settings.kind]
    host, typed_port = split_server(settings.host)
    if not host:
        return ""
    credentials = ""
    if settings.username:
        credentials = (
            quote(settings.username, safe="") + ":"
            + quote(settings.password, safe="") + "@"
        )
    # Bracket IPv6 literals so the port separator stays unambiguous.
    if _is_ipv6(host):
        host = f"[{host}]"
    port = settings.port or typed_port
    port = f":{port}" if port else ""
    return f"{scheme}://{credentials}{host}{port}"


def _is_ipv6(text):
    try:
        return ipaddress.ip_address(text.strip("[]")).version == 6
    except ValueError:
        return False
