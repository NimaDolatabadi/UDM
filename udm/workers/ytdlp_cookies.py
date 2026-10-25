"""Browser cookies loaded into a yt-dlp cookie jar.

Passing cookies as a ``Cookie`` header makes yt-dlp warn and guess their
scope. Loading them as real cookies keeps each one bound to the domain and
path the browser reported.
"""

from http.cookiejar import Cookie
from urllib.parse import urlparse


def _cookie(name, value, domain, path="/", secure=False, expires=None, host_only=True):
    domain = domain if host_only or domain.startswith(".") else f".{domain}"
    return Cookie(
        version=0,
        name=name,
        value=value,
        port=None,
        port_specified=False,
        domain=domain,
        domain_specified=not host_only,
        domain_initial_dot=domain.startswith("."),
        path=path or "/",
        path_specified=True,
        secure=bool(secure),
        expires=int(expires) if expires else None,
        discard=not expires,
        comment=None,
        comment_url=None,
        rest={},
    )


def load_cookies(jar, url, cookie_jar=(), cookie_header=""):
    """Add browser cookies to ``jar`` and return how many were added.

    ``cookie_jar`` holds the extension's cookie records (``name``, ``value``,
    ``domain``, ``path``, ``secure``, ``hostOnly``, ``expirationDate``). When
    it is empty, ``cookie_header`` is parsed and scoped to the URL's host.
    """
    added = 0
    for record in cookie_jar:
        if not record.get("name") or not record.get("domain"):
            continue
        jar.set_cookie(
            _cookie(
                record["name"],
                record.get("value", ""),
                record["domain"],
                record.get("path", "/"),
                record.get("secure", False),
                record.get("expirationDate"),
                record.get("hostOnly", True),
            )
        )
        added += 1
    if added or not cookie_header:
        return added
    host = urlparse(url).hostname or ""
    for pair in cookie_header.split(";"):
        name, separator, value = pair.strip().partition("=")
        if separator and name and host:
            jar.set_cookie(_cookie(name, value, host))
            added += 1
    return added
