"""Operating-system startup registration."""

import logging
from pathlib import Path
import sys


def set_system_startup(enable, executable=None, script_path=None):
    """Enable or disable launching UDM when the current user signs in."""
    executable = executable or sys.executable
    script_path = script_path or str(Path(sys.argv[0]).resolve())

    if sys.platform == "darwin":
        _set_macos_startup(enable, executable, script_path)
    elif sys.platform.startswith("win"):
        _set_windows_startup(enable, executable, script_path)


def _set_macos_startup(enable, executable, script_path):
    plist_path = Path.home() / "Library/LaunchAgents/com.udm.manager.plist"
    if not enable:
        try:
            plist_path.unlink(missing_ok=True)
        except OSError as error:
            logging.error("Failed to remove startup plist: %s", error)
        return

    content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.udm.manager</string>
  <key>ProgramArguments</key>
  <array>
    <string>{executable}</string>
    <string>{script_path}</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
</dict>
</plist>
"""
    try:
        plist_path.parent.mkdir(parents=True, exist_ok=True)
        plist_path.write_text(content, encoding="utf-8")
    except OSError as error:
        logging.error("Failed to set startup plist: %s", error)


def _set_windows_startup(enable, executable, script_path):
    import winreg

    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            key_path,
            0,
            winreg.KEY_ALL_ACCESS,
        )
        if enable:
            command = f'"{executable}" "{script_path}"'
            winreg.SetValueEx(key, "UDMManager", 0, winreg.REG_SZ, command)
        else:
            try:
                winreg.DeleteValue(key, "UDMManager")
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
    except OSError as error:
        logging.error("Failed to set Windows registry startup: %s", error)
