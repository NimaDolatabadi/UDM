"""Windows registry entries that point browsers at a host manifest.

On Windows, Chromium browsers and Firefox find a native-messaging host by
reading the default value of ``<browser key>\\com.udm.capture`` under
``HKEY_CURRENT_USER``, which holds the manifest file's path.
"""

from udm.bridge.protocol import NATIVE_HOST_NAME


def register(base_key, manifest_path, winreg_module=None):
    """Point ``base_key``'s host entry at ``manifest_path``.

    Returns whether the registry changed; a matching value is left alone.
    Raises ``OSError`` when the key cannot be written.
    """
    if winreg_module is None:
        import winreg as winreg_module

    subkey = f"{base_key}\\{NATIVE_HOST_NAME}"
    desired = str(manifest_path)
    access = winreg_module.KEY_READ | winreg_module.KEY_SET_VALUE
    key = winreg_module.CreateKeyEx(
        winreg_module.HKEY_CURRENT_USER, subkey, 0, access
    )
    with key:
        try:
            current, _ = winreg_module.QueryValueEx(key, "")
        except FileNotFoundError:
            current = None
        if current == desired:
            return False
        winreg_module.SetValueEx(key, "", 0, winreg_module.REG_SZ, desired)
    return True
