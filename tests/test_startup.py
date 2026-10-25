"""Tests for idempotent platform startup reconciliation."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from udm.startup import (
    WINDOWS_VALUE_NAME,
    _macos_plist_content,
    _sync_macos_startup,
    _sync_windows_startup,
)


class FakeRegistryKey:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class FakeWinreg:
    HKEY_CURRENT_USER = object()
    KEY_READ = 1
    KEY_SET_VALUE = 2
    REG_SZ = 1

    def __init__(self, value=None, key_exists=True):
        self.value = value
        self.key_exists = key_exists
        self.set_calls = []
        self.delete_calls = []

    def CreateKeyEx(self, *args):
        self.key_exists = True
        return FakeRegistryKey()

    def OpenKey(self, *args):
        if not self.key_exists:
            raise FileNotFoundError
        return FakeRegistryKey()

    def QueryValueEx(self, key, name):
        if self.value is None:
            raise FileNotFoundError
        return self.value, self.REG_SZ

    def SetValueEx(self, key, name, reserved, value_type, value):
        self.set_calls.append((name, value))
        self.value = value

    def DeleteValue(self, key, name):
        self.delete_calls.append(name)
        self.value = None


class StartupTests(unittest.TestCase):
    def test_macos_matching_plist_is_not_rewritten(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "startup.plist"
            path.write_bytes(_macos_plist_content("/python", "/app.py"))
            with patch.object(Path, "write_bytes") as write:
                _sync_macos_startup(True, "/python", "/app.py", path)
            write.assert_not_called()

    def test_macos_changed_command_is_rewritten_and_disabled_is_removed(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "startup.plist"
            path.write_bytes(_macos_plist_content("/old-python", "/app.py"))
            _sync_macos_startup(True, "/new-python", "/app.py", path)
            self.assertEqual(
                path.read_bytes(),
                _macos_plist_content("/new-python", "/app.py"),
            )
            _sync_macos_startup(False, "/new-python", "/app.py", path)
            self.assertFalse(path.exists())

    def test_windows_matching_command_is_not_rewritten(self):
        registry = FakeWinreg('"/python" "/app.py"')
        _sync_windows_startup(
            True,
            "/python",
            "/app.py",
            winreg_module=registry,
        )
        self.assertFalse(registry.set_calls)

    def test_windows_changed_command_is_rewritten_and_disabled_is_removed(self):
        registry = FakeWinreg('"/old-python" "/app.py"')
        _sync_windows_startup(
            True,
            "/new-python",
            "/app.py",
            winreg_module=registry,
        )
        self.assertEqual(
            registry.set_calls,
            [(WINDOWS_VALUE_NAME, '"/new-python" "/app.py"')],
        )
        _sync_windows_startup(
            False,
            "/new-python",
            "/app.py",
            winreg_module=registry,
        )
        self.assertEqual(registry.delete_calls, [WINDOWS_VALUE_NAME])


if __name__ == "__main__":
    unittest.main()
