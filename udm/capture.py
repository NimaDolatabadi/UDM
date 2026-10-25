"""Validated download requests captured from the browser extension."""

from dataclasses import dataclass, field
import re
from urllib.parse import urlparse

FILE_KIND = "file"
STREAM_KIND = "stream"

# Extension message types mapped to the download engine that serves them.
# "formats" asks for available qualities and is resolved like a stream.
_MESSAGE_KINDS = {"download": FILE_KIND, "stream": STREAM_KIND, "formats": STREAM_KIND}
_MAX_FIELD_LENGTH = 64 * 1024
_MAX_COOKIES = 500
_QUALITY = re.compile(r"best|audio|\d{3,4}p", re.IGNORECASE)


@dataclass(frozen=True)
class CaptureRequest:
    """One link plus the browser session details needed to fetch it.

    ``kind`` is ``file`` for direct HTTP transfers and ``stream`` for pages and
    HLS or DASH manifests that yt-dlp resolves and merges. ``quality`` is empty
    (use the configured default), ``best``, ``audio``, or a height like
    ``720p``. ``cookie_jar`` holds the browser's cookie records for yt-dlp.
    """

    url: str
    kind: str = FILE_KIND
    referrer: str = ""
    cookies: str = ""
    user_agent: str = ""
    filename: str = ""
    title: str = ""
    quality: str = ""
    cookie_jar: tuple = field(default=(), compare=False)

    @classmethod
    def from_message(cls, message):
        """Build a request from an extension message.

        Raises ``ValueError`` for unknown message types, non-HTTP URLs, or
        malformed fields, so untrusted input never reaches a worker.
        """
        if not isinstance(message, dict):
            raise ValueError("Message must be an object")
        kind = _MESSAGE_KINDS.get(message.get("type"))
        if kind is None:
            raise ValueError(f"Unsupported message type: {message.get('type')!r}")
        url = _text(message, "url").strip()
        if urlparse(url).scheme not in ("http", "https"):
            raise ValueError("Only HTTP and HTTPS links can be captured")
        quality = _text(message, "quality").strip()
        if quality and not _QUALITY.fullmatch(quality):
            raise ValueError(f"Unsupported quality: {quality!r}")
        return cls(
            url=url,
            kind=kind,
            referrer=_text(message, "referrer"),
            cookies=_text(message, "cookies"),
            user_agent=_text(message, "userAgent"),
            filename=_text(message, "filename"),
            title=_text(message, "title"),
            quality=quality.lower(),
            cookie_jar=_cookie_records(message.get("cookieJar")),
        )

    def headers(self):
        """Return HTTP headers that reproduce the browser session."""
        headers = self.stream_headers()
        if self.cookies:
            headers["Cookie"] = self.cookies
        return headers

    def stream_headers(self):
        """Return session headers without cookies, which yt-dlp takes as a jar."""
        headers = {}
        if self.user_agent:
            headers["User-Agent"] = self.user_agent
        if self.referrer:
            headers["Referer"] = self.referrer
        return headers

    def display_name(self):
        """Return the label shown in the queue before a filename is known."""
        return self.title or self.filename or self.url


def _text(message, key):
    value = message.get(key, "")
    if value is None:
        return ""
    if not isinstance(value, str) or len(value) > _MAX_FIELD_LENGTH:
        raise ValueError(f"Field {key!r} must be a string")
    # Header values cannot contain line breaks; reject header injection.
    if key != "title" and ("\r" in value or "\n" in value):
        raise ValueError(f"Field {key!r} contains a line break")
    return value


def _cookie_records(records):
    """Return validated cookie records as plain dictionaries."""
    if records is None:
        return ()
    if not isinstance(records, list) or len(records) > _MAX_COOKIES:
        raise ValueError("Field 'cookieJar' must be a list of cookies")
    cleaned = []
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("Each cookie must be an object")
        cookie = {}
        for key in ("name", "value", "domain", "path"):
            value = record.get(key, "")
            if not isinstance(value, str) or len(value) > 8192 or "\n" in value:
                raise ValueError(f"Cookie field {key!r} is invalid")
            cookie[key] = value
        cookie["secure"] = bool(record.get("secure", False))
        cookie["hostOnly"] = bool(record.get("hostOnly", True))
        expires = record.get("expirationDate")
        cookie["expirationDate"] = expires if isinstance(expires, (int, float)) else None
        cleaned.append(cookie)
    return tuple(cleaned)
