"""Server-reported filenames and collision-free destination paths."""

import mimetypes
from pathlib import Path, PurePosixPath
import re
from urllib.parse import unquote, urlparse

_MAX_NAME_LENGTH = 200
# Types common for downloads that the platform MIME table may not know.
_EXTENSION_FOR_TYPE = {
    "application/x-apple-diskimage": ".dmg",
    "application/x-diskcopy": ".dmg",
    "application/vnd.apple.installer+xml": ".pkg",
    "application/x-newton-compatible-pkg": ".pkg",
    "application/vnd.android.package-archive": ".apk",
    "application/x-msdownload": ".exe",
    "application/x-msdos-program": ".exe",
    "application/x-msi": ".msi",
    "application/x-7z-compressed": ".7z",
    "application/x-rar-compressed": ".rar",
    "application/vnd.rar": ".rar",
    "application/zip": ".zip",
    "application/x-bittorrent": ".torrent",
}
# Generic types say nothing about the file and must not add an extension.
_GENERIC_TYPES = {"application/octet-stream", "binary/octet-stream", "text/html", ""}


def sanitize(name):
    """Return ``name`` safe to use as one path component, or an empty string."""
    name = re.sub(r"[\x00-\x1f\x7f/\\:]", "_", name or "").strip().strip(".")
    if len(name) > _MAX_NAME_LENGTH:
        stem, dot, suffix = name.rpartition(".")
        keep = _MAX_NAME_LENGTH - len(suffix) - 1
        name = f"{stem[:keep]}.{suffix}" if dot and keep > 0 else name[:_MAX_NAME_LENGTH]
    return name


def from_content_disposition(header):
    """Return the filename in a ``Content-Disposition`` header, if any.

    The RFC 5987 ``filename*`` form wins over the plain ``filename`` form.
    """
    if not header:
        return ""
    extended = re.search(r"filename\*\s*=\s*([^']*)'[^']*'([^;]+)", header, re.I)
    if extended:
        encoding = extended.group(1) or "utf-8"
        try:
            return sanitize(unquote(extended.group(2).strip().strip('"'), encoding))
        except LookupError:
            return sanitize(unquote(extended.group(2).strip().strip('"')))
    plain = re.search(r'filename\s*=\s*"([^"]*)"|filename\s*=\s*([^;]+)', header, re.I)
    if plain:
        return sanitize(unquote((plain.group(1) or plain.group(2) or "").strip()))
    return ""


def from_url(url):
    """Return the last path segment of ``url`` when it has an extension."""
    name = sanitize(unquote(PurePosixPath(urlparse(url).path).name))
    return name if PurePosixPath(name).suffix else ""


def extension_for_type(content_type):
    """Return a file extension for a specific ``Content-Type``, or ``""``."""
    media_type = (content_type or "").split(";")[0].strip().lower()
    if media_type in _GENERIC_TYPES:
        return ""
    return _EXTENSION_FOR_TYPE.get(media_type) or mimetypes.guess_extension(media_type) or ""


def remote_filename(final_url, headers, fallback):
    """Return the best filename for a response, or ``""`` when nothing improves.

    Prefers ``Content-Disposition``, then the post-redirect URL, then
    ``fallback`` with an extension inferred from ``Content-Type`` when the
    fallback has none.
    """
    headers = headers or {}
    name = from_content_disposition(headers.get("content-disposition", ""))
    if name:
        return name
    name = from_url(final_url or "")
    if name:
        return name
    if fallback and not PurePosixPath(fallback).suffix:
        extension = extension_for_type(headers.get("content-type", ""))
        if extension:
            return f"{fallback}{extension}"
    return ""


def claim_unique_path(directory, filename, attempts=100):
    """Atomically create an empty file at a unique path and return it.

    Creating the placeholder reserves the name, so concurrent downloads that
    resolve to the same filename never write to one destination.
    """
    Path(directory).mkdir(parents=True, exist_ok=True)
    for _ in range(attempts):
        candidate = unique_path(directory, filename)
        try:
            with candidate.open("x"):
                return candidate
        except FileExistsError:
            continue
    raise FileExistsError(f"No free name for {filename} in {directory}")


def unique_path(directory, filename, reserved=()):
    """Return ``directory/filename``, numbered to avoid existing or reserved paths."""
    candidate = Path(directory) / filename
    reserved = {str(path) for path in reserved}
    counter = 1
    while str(candidate) in reserved or candidate.exists():
        stem, suffix = PurePosixPath(filename).stem, PurePosixPath(filename).suffix
        candidate = Path(directory) / f"{stem} ({counter}){suffix}"
        counter += 1
    return candidate
