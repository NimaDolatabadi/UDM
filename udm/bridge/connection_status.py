"""Last contact from the browser extension, for the Browser options page.

Native messaging only lets the extension start a conversation, so UDM cannot
ask whether it is installed. Instead, the native host and the app record each
message that identifies its extension, and the Browser page reports the most
recent contact per browser engine. The record is a small JSON file in the
data directory, so it survives restarts and is shared by both processes.
"""

from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path

from udm import paths

STATUS_FILE = "extension-status.json"
_ENGINES = ("chromium", "firefox", "safari")


def status_path(data_dir=None):
    """Return the status file inside ``data_dir``."""
    return Path(data_dir or paths.data_dir()) / STATUS_FILE


def record(message, data_dir=None, now=None):
    """Store the sender of ``message`` as the engine's latest contact.

    Messages without a known ``engine`` field, such as those from extensions
    released before it existed, are ignored. Write failures are logged and
    never reach the browser.
    """
    engine = message.get("engine")
    if engine not in _ENGINES:
        return False
    protocol = message.get("protocol", 1)
    entries = load(data_dir)
    entries[engine] = {
        "version": str(message.get("extensionVersion", ""))[:32],
        "protocol": protocol if isinstance(protocol, int) else 1,
        "seen": (now or datetime.now(timezone.utc)).isoformat(timespec="seconds"),
    }
    try:
        path = status_path(data_dir)
        # A per-process name keeps the host and the app from sharing a
        # temporary file.
        temporary = path.with_name(f"{path.name}.{os.getpid()}.tmp")
        temporary.write_text(json.dumps(entries, indent=2), encoding="utf-8")
        # Replacing keeps a concurrent reader from seeing half a file.
        os.replace(temporary, path)
    except OSError as error:
        logging.warning("Could not record extension contact: %s", error)
        return False
    return True


def load(data_dir=None):
    """Return the recorded contacts keyed by engine; empty when unreadable."""
    try:
        entries = json.loads(status_path(data_dir).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return entries if isinstance(entries, dict) else {}


def describe(entry, now=None):
    """Return a sentence describing one recorded contact, or ``None``."""
    if not isinstance(entry, dict):
        return None
    try:
        seen = datetime.fromisoformat(entry["seen"])
    except (KeyError, TypeError, ValueError):
        return None
    version = entry.get("version") or "unknown version"
    return f"UDM Capture {version} last connected {_ago(seen, now)}."


def _ago(moment, now=None):
    now = now or datetime.now(timezone.utc)
    seconds = max(0, int((now - moment).total_seconds()))
    if seconds < 60:
        return "just now"
    for size, unit in ((86400, "day"), (3600, "hour"), (60, "minute")):
        if seconds >= size:
            count = seconds // size
            return f"{count} {unit}{'s' if count != 1 else ''} ago"
    return "just now"
