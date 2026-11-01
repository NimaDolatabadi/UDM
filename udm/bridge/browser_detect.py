"""Find installed browsers and open files or pages with platform tools.

Detection looks where each platform installs browsers for the current user:
Applications folders on macOS, ``PATH`` on Linux, and Program Files or Local
AppData on Windows. It never launches a browser.
"""

import os
from pathlib import Path
import shutil
import subprocess

from udm import paths


def locate(browser, platform=None, roots=None, which=shutil.which):
    """Return the app bundle or executable of ``browser``, or ``None``.

    ``roots`` replaces the platform's search folders, and ``which`` the
    ``PATH`` lookup, so tests can describe any machine.
    """
    platform = platform or paths.platform_key()
    if platform == paths.LINUX:
        for command in browser.linux_commands:
            found = which(command)
            if found:
                return Path(found)
        return None
    if platform == paths.WINDOWS:
        names, roots = browser.windows_exes, roots or windows_roots()
    else:
        names, roots = browser.mac_apps, roots or mac_roots()
    for root in roots:
        for name in names:
            # Windows names use backslashes; split them so any host resolves them.
            candidate = Path(root).joinpath(*name.split("\\"))
            if candidate.exists():
                return candidate
    return None


def mac_roots():
    """Return the Applications folders searched on macOS."""
    return (Path("/Applications"), Path.home() / "Applications")


def windows_roots(environ=None):
    """Return the Windows folders that hold per-machine and per-user installs."""
    environ = os.environ if environ is None else environ
    names = ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA")
    return tuple(Path(environ[name]) for name in names if environ.get(name))


def reveal_command(path, platform=None):
    """Return the command that shows ``path`` in the file manager."""
    platform = platform or paths.platform_key()
    if platform == paths.DARWIN:
        return ["open", "-R", str(path)]
    if platform == paths.WINDOWS:
        return ["explorer", f"/select,{path}"]
    return ["xdg-open", str(Path(path).parent)]


def open_url_command(app, url, platform=None):
    """Return the command that opens ``url`` in the browser at ``app``."""
    platform = platform or paths.platform_key()
    if platform == paths.DARWIN:
        return ["open", "-a", str(app), url]
    return [str(app), url]


def spawn(command):
    """Start ``command`` detached, without waiting for it to exit.

    Browsers started from here must outlive UDM, so nothing waits for them or
    kills them on a timeout.
    """
    options = {}
    if paths.platform_key() != paths.WINDOWS:
        options["start_new_session"] = True
    return subprocess.Popen(
        command,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        **options,
    )


def run_quietly(commands, runner=spawn):
    """Start each command, ignoring failures.

    Browsers may refuse internal pages such as ``chrome://extensions`` from
    the command line, and the caller always shows written steps as well.
    """
    for command in commands:
        try:
            runner(command)
        except (OSError, subprocess.SubprocessError):
            pass
