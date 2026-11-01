"""Tests for native-host registration on macOS, Linux, and Windows."""

import json
from pathlib import Path
import tempfile
import unittest

from udm import paths
from udm.bridge import host_registration
from udm.bridge.browsers import browser_by_key, supported_browsers
from udm.bridge.protocol import NATIVE_HOST_NAME

COMMAND = ["/opt/udm/UDM"]
MANIFEST = f"{NATIVE_HOST_NAME}.json"


class FakeWinreg:
    """Store registry default values in a dictionary."""

    HKEY_CURRENT_USER = "HKCU"
    KEY_READ = 1
    KEY_SET_VALUE = 2
    REG_SZ = 1

    def __init__(self):
        self.values = {}
        self.writes = 0

    class _Key:
        def __init__(self, store, path):
            self.store, self.path = store, path

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    def CreateKeyEx(self, root, subkey, reserved, access):
        return self._Key(self, subkey)

    def QueryValueEx(self, key, name):
        if key.path not in self.values:
            raise FileNotFoundError(key.path)
        return self.values[key.path], self.REG_SZ

    def SetValueEx(self, key, name, reserved, kind, value):
        self.values[key.path] = value
        self.writes += 1


class RegistrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name) / "home"
        self.data = Path(self.temp.name) / "data"

    def _register(self, key, platform, **options):
        return host_registration.register(
            browser_by_key(key), self.home, self.data, COMMAND, platform, **options
        )

    def test_linux_writes_xdg_locations(self):
        chrome = self._register("chrome", paths.LINUX)
        firefox = self._register("firefox", paths.LINUX)
        self.assertEqual(chrome.manifests, (
            self.home / ".config/google-chrome/NativeMessagingHosts" / MANIFEST,
        ))
        self.assertEqual(firefox.manifests, (
            self.home / ".mozilla/native-messaging-hosts" / MANIFEST,
        ))
        manifest = json.loads(firefox.manifests[0].read_text())
        self.assertIn("allowed_extensions", manifest)
        self.assertIn("exec /opt/udm/UDM --native-messaging-host", chrome.wrapper.read_text())

    def test_macos_writes_application_support(self):
        result = self._register("edge", paths.DARWIN)
        support = self.home / "Library/Application Support"
        self.assertEqual(result.manifests, (
            support / "Microsoft Edge/NativeMessagingHosts" / MANIFEST,
        ))

    def test_windows_points_registry_keys_at_a_batch_wrapper(self):
        winreg = FakeWinreg()
        result = self._register("brave", paths.WINDOWS, winreg_module=winreg)
        manifest_path = self.data / "native-host" / "chromium" / MANIFEST
        self.assertEqual(result.manifests, (manifest_path,))
        self.assertEqual(result.wrapper.name, "udm-native-host.bat")
        self.assertEqual(
            result.wrapper.read_bytes(),
            b'@echo off\r\n"/opt/udm/UDM" --native-messaging-host %*\r\n',
        )
        self.assertEqual(json.loads(manifest_path.read_text())["path"], str(result.wrapper))
        self.assertEqual(set(winreg.values.values()), {str(manifest_path)})
        self.assertIn(
            rf"Software\Google\Chrome\NativeMessagingHosts\{NATIVE_HOST_NAME}", winreg.values
        )

    def test_registering_twice_changes_nothing(self):
        winreg = FakeWinreg()
        self.assertTrue(self._register("chrome", paths.WINDOWS, winreg_module=winreg).changed)
        again = self._register("chrome", paths.WINDOWS, winreg_module=winreg)
        self.assertEqual(again.changed, ())
        self.assertEqual(winreg.writes, 1)

    def test_stale_manifest_is_repaired(self):
        first = self._register("firefox", paths.LINUX)
        first.manifests[0].write_text('{"path": "/old/UDM"}')
        repaired = self._register("firefox", paths.LINUX)
        self.assertEqual(repaired.changed, first.manifests)
        self.assertEqual(
            json.loads(first.manifests[0].read_text())["path"], str(first.wrapper)
        )


class SyncTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name) / "home"
        self.data = Path(self.temp.name) / "data"

    def _sync(self, installed_keys, platform=paths.LINUX):
        return host_registration.sync_all(
            self.home, self.data, COMMAND, platform,
            installed=lambda browser: browser.key in installed_keys,
        )

    def test_only_installed_browsers_get_new_manifests(self):
        changed = self._sync({"firefox"})
        manifests = [path for path in changed if path.name == MANIFEST]
        self.assertEqual(manifests, [
            self.home / ".mozilla/native-messaging-hosts" / MANIFEST,
        ])
        self.assertEqual(self._sync({"firefox"}), [])

    def test_undetected_browsers_have_existing_manifests_repaired_only(self):
        self._sync({"chrome"})
        stale = self.home / ".config/google-chrome/NativeMessagingHosts" / MANIFEST
        stale.write_text("{}")
        changed = self._sync(set())
        self.assertIn(stale, changed)
        # Opera reads Chrome's folder too, but gets no folder of its own.
        self.assertFalse((self.home / ".config/chromium").exists())

    def test_one_failing_browser_does_not_stop_the_others(self):
        blocked = self.home / ".config"
        blocked.parent.mkdir(parents=True)
        blocked.write_text("not a folder")
        changed = self._sync({"chrome", "firefox"})
        self.assertIn(self.home / ".mozilla/native-messaging-hosts" / MANIFEST, changed)

    def test_safari_is_never_registered(self):
        self.assertIn(browser_by_key("safari"), supported_browsers(paths.DARWIN))
        changed = self._sync({"safari"}, paths.DARWIN)
        self.assertEqual(changed, [])


if __name__ == "__main__":
    unittest.main()
