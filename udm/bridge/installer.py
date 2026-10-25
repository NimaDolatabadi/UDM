"""Per-browser installation of the extension files and native host.

Browsers do not let applications add extensions silently, so installation
prepares everything the browser needs and then guides the user through the
one manual step: loading the unpacked extension folder.
"""

from dataclasses import dataclass
import json
from pathlib import Path
import shlex
import subprocess

from udm import __version__, paths
from udm.bridge import extension_build
from udm.bridge.browsers import FIREFOX
from udm.bridge.protocol import NATIVE_HOST_NAME

HOST_FLAG = "--native-messaging-host"


@dataclass(frozen=True)
class InstallResult:
    """Paths written by an installation and the remaining manual steps."""

    extension_dir: Path
    host_wrapper: Path
    host_manifests: tuple
    steps: tuple


def install(browser, home=None, data_dir=None, host_command=None, source=None):
    """Prepare ``browser`` to use the extension and return what was written."""
    home = Path(home or Path.home())
    data_dir = Path(data_dir or paths.data_dir())
    extension_dir = extension_build.build_extension(
        browser.engine,
        data_dir / "extension" / browser.engine,
        __version__,
        source,
    )
    wrapper = write_host_wrapper(
        data_dir / "native-host" / "udm-native-host",
        host_command or paths.app_command(),
    )
    manifest = host_manifest(browser.engine, wrapper, source)
    support = home / "Library" / "Application Support"
    written = []
    for relative in browser.host_dirs:
        target = support / relative / f"{NATIVE_HOST_NAME}.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        written.append(target)
    return InstallResult(
        extension_dir, wrapper, tuple(written), setup_steps(browser, extension_dir)
    )


def write_host_wrapper(path, command):
    """Write an executable script that starts the native host.

    Host manifests accept only an executable path without arguments, so the
    wrapper supplies the interpreter, entry script, and host flag.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    quoted = " ".join(shlex.quote(str(part)) for part in command)
    path.write_text(
        f'#!/bin/sh\nexec {quoted} {HOST_FLAG} "$@"\n', encoding="utf-8"
    )
    path.chmod(0o755)
    return path


def host_manifest(engine, wrapper, source=None):
    """Return the native-host manifest that authorizes the UDM extension."""
    manifest = {
        "name": NATIVE_HOST_NAME,
        "description": "UDM browser capture bridge",
        "path": str(wrapper),
        "type": "stdio",
    }
    if engine == FIREFOX:
        manifest["allowed_extensions"] = [
            extension_build.firefox_extension_id(source)
        ]
    else:
        extension_id = extension_build.chromium_extension_id(source)
        manifest["allowed_origins"] = [f"chrome-extension://{extension_id}/"]
    return manifest


def setup_steps(browser, extension_dir):
    """Return the manual steps that finish installation in ``browser``."""
    if browser.engine == FIREFOX:
        return (
            f"Open {browser.extensions_url} in Firefox.",
            'Click "Load Temporary Add-on..." and choose '
            f"{extension_dir / 'manifest.json'}.",
            "Firefox removes temporary add-ons when it quits; repeat these "
            "steps after restarting Firefox until the add-on is signed.",
        )
    return (
        f"Open {browser.extensions_url} in {browser.name}.",
        "Turn on Developer mode.",
        f'Click "Load unpacked" and choose {extension_dir}.',
        "Pin UDM Capture to the toolbar. After updating UDM, install again "
        "and click Reload on the extension card.",
    )


def open_setup_pages(browser, result, runner=subprocess.run):
    """Reveal the extension folder and open the browser's extensions page.

    Failures are ignored: some browsers refuse internal URLs from the command
    line, and the written steps still explain where to go.
    """
    commands = [["open", "-R", str(result.extension_dir / "manifest.json")]]
    app = browser.app_path()
    if app is not None:
        commands.append(["open", "-a", str(app), browser.extensions_url])
    for command in commands:
        try:
            runner(command, check=False, timeout=10)
        except (OSError, subprocess.SubprocessError):
            pass
