"""Idempotent operating-system startup registration."""

import logging
from pathlib import Path
import plistlib
import sys

STARTUP_LABEL = "com.udm.manager"
WINDOWS_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
WINDOWS_VALUE_NAME = "UDMManager"


def sync_system_startup(enable, executable=None, script_path=None):
    """Reconcile the current user's startup entry with the desired command."""
    executable = executable or sys.executable
    script_path = script_path or str(Path(sys.argv[0]).resolve())

    if sys.platform == "darwin":
        _sync_macos_startup(enable, executable, script_path)
    elif sys.platform.startswith("win"):
        _sync_windows_startup(enable, executable, script_path)


def set_system_startup(enable, executable=None, script_path=None):
    """Apply a startup preference immediately when an option changes."""
    sync_system_startup(enable, executable, script_path)


def _macos_plist_content(executable, script_path):
    return plistlib.dumps(
        {
            "Label": STARTUP_LABEL,
            "ProgramArguments": [executable, script_path],
            "RunAtLoad": True,
        },
        fmt=plistlib.FMT_XML,
        sort_keys=False,
    )


def _sync_macos_startup(
    enable,
    executable,
    script_path,
    plist_path=None,
):
    plist_path = plist_path or (
        Path.home() / "Library/LaunchAgents/com.udm.manager.plist"
    )
    try:
        if not enable:
            if plist_path.exists():
                plist_path.unlink()
            return
        desired = _macos_plist_content(executable, script_path)
        if plist_path.exists() and plist_path.read_bytes() == desired:
            return
        plist_path.parent.mkdir(parents=True, exist_ok=True)
        plist_path.write_bytes(desired)
    except OSError as error:
        logging.error("Failed to reconcile startup plist: %s", error)


def _sync_windows_startup(
    enable,
    executable,
    script_path,
    winreg_module=None,
):
    if winreg_module is None:
        import winreg as winreg_module

    desired = f'"{executable}" "{script_path}"'
    access = winreg_module.KEY_READ | winreg_module.KEY_SET_VALUE
    try:
        if enable:
            key = winreg_module.CreateKeyEx(
                winreg_module.HKEY_CURRENT_USER,
                WINDOWS_RUN_KEY,
                0,
                access,
            )
        else:
            try:
                key = winreg_module.OpenKey(
                    winreg_module.HKEY_CURRENT_USER,
                    WINDOWS_RUN_KEY,
                    0,
                    access,
                )
            except FileNotFoundError:
                return
        with key:
            try:
                current, _ = winreg_module.QueryValueEx(
                    key,
                    WINDOWS_VALUE_NAME,
                )
            except FileNotFoundError:
                current = None
            if enable and current != desired:
                winreg_module.SetValueEx(
                    key,
                    WINDOWS_VALUE_NAME,
                    0,
                    winreg_module.REG_SZ,
                    desired,
                )
            elif not enable and current is not None:
                winreg_module.DeleteValue(key, WINDOWS_VALUE_NAME)
    except OSError as error:
        logging.error("Failed to reconcile Windows registry startup: %s", error)
