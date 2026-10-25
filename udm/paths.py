"""Filesystem locations and launch commands for source and bundled runs."""

import hashlib
import os
from pathlib import Path
import shutil
import sys
import tempfile

APP_NAME = "UDM"
# macOS limits Unix socket paths to 104 bytes including the terminator.
_MAX_SOCKET_PATH = 100
_PACKAGE_ROOT = Path(__file__).resolve().parent.parent


def is_frozen():
    """Return whether the process runs from a PyInstaller bundle."""
    return bool(getattr(sys, "frozen", False))


def resource_dir():
    """Return the directory holding bundled resources such as ``extension/``."""
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return _PACKAGE_ROOT


def resource_path(*parts):
    """Return the path of a bundled resource."""
    return resource_dir().joinpath(*parts)


def data_dir():
    """Return and create the per-user application data directory.

    ``UDM_DATA_DIR`` overrides the platform location, which keeps tests and
    development runs away from a real installation.
    """
    override = os.environ.get("UDM_DATA_DIR")
    if override:
        path = Path(override)
    elif sys.platform == "darwin":
        path = Path.home() / "Library" / "Application Support" / APP_NAME
    elif sys.platform.startswith("win"):
        path = Path(os.environ.get("APPDATA", Path.home())) / APP_NAME
    else:
        base = os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share"
        path = Path(base) / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def log_file(name="download_manager.log"):
    """Return the path of a log file inside the data directory."""
    logs = data_dir() / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    return logs / name


def bridge_socket_path():
    """Return the local socket path shared by the app and the native host.

    The socket lives in the data directory unless that path exceeds the Unix
    socket length limit; then a short per-user, per-data-directory name in the
    system temporary directory is used, derived identically by both processes.
    """
    preferred = data_dir() / "bridge.sock"
    if len(os.fsencode(preferred)) <= _MAX_SOCKET_PATH:
        return preferred
    digest = hashlib.sha256(os.fsencode(data_dir())).hexdigest()[:12]
    return Path(tempfile.gettempdir()) / f"udm-{os.getuid()}-{digest}.sock"


def resolve_config_path(legacy_dir=None):
    """Return the settings file path, migrating a legacy working-directory copy.

    Versions before 0.6.0 stored ``udm_config.json`` in the working directory,
    which is ``/`` for login items and app bundles. An existing legacy file is
    copied once so source checkouts keep their settings.
    """
    target = data_dir() / "udm_config.json"
    legacy = Path(legacy_dir or Path.cwd()) / "udm_config.json"
    if not target.exists() and legacy.is_file():
        try:
            shutil.copy2(legacy, target)
        except OSError:
            pass
    return target


def app_command():
    """Return the argument list that launches the desktop application."""
    if is_frozen():
        return [sys.executable]
    return [sys.executable, str(_PACKAGE_ROOT / "MACDM.py")]


def app_bundle():
    """Return the enclosing ``.app`` bundle of a frozen macOS build, if any."""
    if not is_frozen():
        return None
    for parent in Path(sys.executable).resolve().parents:
        if parent.suffix == ".app":
            return parent
    return None
