"""Register UDM as the browsers' native-messaging host.

The host manifest tells a browser which program to start for the extension
and which extension IDs may use it. Browsers cannot create it themselves, so
UDM writes it at every launch for each installed browser, and repairs stale
copies, for example after UDM moved or was updated. Writing is idempotent:
files and registry values that already match are left untouched.
"""

from dataclasses import dataclass
import json
import logging
from pathlib import Path
import shlex

from udm import paths
from udm.bridge import extension_build, windows_hosts
from udm.bridge.browsers import FIREFOX, SAFARI, supported_browsers
from udm.bridge.protocol import NATIVE_HOST_NAME

HOST_FLAG = "--native-messaging-host"
# TODO: Add the IDs the Chrome Web Store and Edge Add-ons assign once the
# extension is published there. Issue #16.
CHROMIUM_STORE_IDS = ()
# Signing through addons.mozilla.org keeps the Gecko ID from the manifest.
FIREFOX_STORE_IDS = ()


@dataclass(frozen=True)
class Registration:
    """Where one browser's host is registered and what changed.

    ``manifests`` are manifest files; on Windows ``registry_keys`` are the
    registry keys pointing at them. ``changed`` lists every file or key that
    was written because it was missing or stale.
    """

    wrapper: Path
    manifests: tuple
    registry_keys: tuple
    changed: tuple


def host_manifest(engine, wrapper, source=None):
    """Return the native-host manifest that authorizes the UDM extension."""
    manifest = {
        "name": NATIVE_HOST_NAME,
        "description": "UDM browser capture bridge",
        "path": str(wrapper),
        "type": "stdio",
    }
    if engine == FIREFOX:
        ids = [extension_build.firefox_extension_id(source), *FIREFOX_STORE_IDS]
        manifest["allowed_extensions"] = list(dict.fromkeys(ids))
    else:
        ids = [extension_build.chromium_extension_id(source), *CHROMIUM_STORE_IDS]
        manifest["allowed_origins"] = [
            f"chrome-extension://{extension_id}/" for extension_id in dict.fromkeys(ids)
        ]
    return manifest


def wrapper_path(data_dir, platform=None):
    """Return where the host wrapper lives in ``data_dir``."""
    name = "udm-native-host.bat" if _windows(platform) else "udm-native-host"
    return Path(data_dir) / "native-host" / name


def wrapper_content(command, platform=None):
    """Return the wrapper script that starts the native host.

    Host manifests accept only an executable path without arguments, so the
    wrapper supplies the interpreter, entry script, and host flag.
    """
    if _windows(platform):
        quoted = " ".join(f'"{part}"' for part in command)
        return f"@echo off\r\n{quoted} {HOST_FLAG} %*\r\n"
    quoted = " ".join(shlex.quote(str(part)) for part in command)
    return f'#!/bin/sh\nexec {quoted} {HOST_FLAG} "$@"\n'


def manifest_paths(browser, home, data_dir, platform=None):
    """Return the manifest files to write for ``browser``.

    Windows keeps one manifest per engine in the data directory, because the
    registry points at it; the other platforms read fixed folders.
    """
    platform = platform or paths.platform_key()
    filename = f"{NATIVE_HOST_NAME}.json"
    if platform == paths.WINDOWS:
        return (Path(data_dir) / "native-host" / browser.engine / filename,)
    base = Path(home)
    if platform == paths.DARWIN:
        base = base / "Library" / "Application Support"
    return tuple(base / location / filename for location in browser.host_locations(platform))


def register(browser, home=None, data_dir=None, host_command=None, platform=None,
             source=None, winreg_module=None, repair_only=False):
    """Write or repair the host wrapper and manifests for ``browser``.

    With ``repair_only``, only manifests that already exist are rewritten and
    no registry key is created, which updates a browser UDM no longer detects
    without adding files for it. Raises ``OSError`` when a file or registry
    key cannot be written.
    """
    platform = platform or paths.platform_key()
    home = Path(home or Path.home())
    data_dir = Path(data_dir or paths.data_dir())
    changed = []
    wrapper = wrapper_path(data_dir, platform)
    if write_if_changed(wrapper, wrapper_content(host_command or paths.app_command(), platform)):
        changed.append(wrapper)
    if platform != paths.WINDOWS:
        wrapper.chmod(0o755)
    text = json.dumps(host_manifest(browser.engine, wrapper, source), indent=2) + "\n"
    manifests = manifest_paths(browser, home, data_dir, platform)
    if repair_only:
        manifests = tuple(path for path in manifests if path.exists())
    changed.extend(path for path in manifests if write_if_changed(path, text))
    keys = ()
    if platform == paths.WINDOWS and not repair_only:
        keys = browser.host_locations(platform)
    for key in keys:
        if windows_hosts.register(key, manifests[0], winreg_module):
            changed.append(key)
    return Registration(wrapper, manifests, tuple(keys), tuple(changed))


def sync_all(home=None, data_dir=None, host_command=None, platform=None,
             source=None, winreg_module=None, installed=None):
    """Register the host for every installed browser; return what changed.

    For browsers that were not detected, existing UDM manifests are repaired
    and nothing new is written. Failures are logged per browser so one locked
    folder cannot stop the others. ``installed`` replaces browser detection.
    """
    platform = platform or paths.platform_key()
    home = Path(home or Path.home())
    data_dir = Path(data_dir or paths.data_dir())
    installed = installed or (lambda browser: browser.is_installed(platform))
    changed = []
    for browser in supported_browsers(platform):
        if browser.engine == SAFARI:
            continue
        detected = installed(browser)
        existing = any(
            path.exists() for path in manifest_paths(browser, home, data_dir, platform)
        )
        if not (detected or existing):
            continue
        try:
            result = register(
                browser, home, data_dir, host_command, platform, source,
                winreg_module, repair_only=not detected,
            )
        except OSError as error:
            logging.warning("Could not register the host for %s: %s", browser.name, error)
            continue
        changed.extend(item for item in result.changed if item not in changed)
    return changed


def write_if_changed(path, text):
    """Write ``text`` to ``path`` unless it already matches; return whether it did."""
    path = Path(path)
    try:
        # Bytes, not text mode, so CRLF in the Windows wrapper compares exactly.
        if path.read_bytes().decode("utf-8") == text:
            return False
    except (OSError, UnicodeDecodeError):
        pass
    path.parent.mkdir(parents=True, exist_ok=True)
    # newline="" keeps the Windows wrapper's CRLF line endings exact.
    with open(path, "w", encoding="utf-8", newline="") as handle:
        handle.write(text)
    return True


def _windows(platform):
    return (platform or paths.platform_key()) == paths.WINDOWS
