"""Tests for the Safari extension app assembly and its installer branch."""

import json
from pathlib import Path
import plistlib
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from udm.bridge import extension_build, installer, safari
from udm.bridge.browsers import SAFARI, browser_by_key


class FakeRunner:
    """Record subprocess calls and succeed without running anything."""

    def __init__(self):
        self.commands = []

    def __call__(self, command, **kwargs):
        self.commands.append(command)
        return subprocess.CompletedProcess(command, 0, "", "")


class SafariManifestTests(unittest.TestCase):
    def test_manifest_drops_missing_apis_and_adds_link_capture(self):
        manifest = extension_build.load_manifest(SAFARI)
        self.assertNotIn("downloads", manifest["permissions"])
        self.assertNotIn("notifications", manifest["permissions"])
        self.assertIn("nativeMessaging", manifest["permissions"])
        self.assertNotIn("exclude_permissions", manifest)
        self.assertFalse(manifest["background"]["persistent"])
        self.assertIn("links.js", manifest["content_scripts"][0]["js"])


class SafariAppTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.binaries = {}
        for name in ("app", "extension"):
            self.binaries[name] = self.root / name
            self.binaries[name].write_bytes(b"binary")
        self.runner = FakeRunner()

    def _install(self, socket_path="/Users/me/Library/Application Support/UDM/bridge.sock"):
        return safari.install(
            self.root / "data", "1.2.3", socket_path, "/Applications/UDM.app",
            binaries=self.binaries, runner=self.runner,
        )

    def test_app_bundles_extension_handler_and_bridge_settings(self):
        app = self._install()
        appex = app / "Contents/PlugIns/UDM Capture Extension.appex"
        resources = appex / "Contents/Resources"
        manifest = json.loads((resources / "manifest.json").read_text())
        self.assertEqual(manifest["version"], "1.2.3")
        self.assertTrue((resources / "links.js").is_file())
        self.assertTrue((appex / "Contents/MacOS/UDMCaptureExtension").is_file())
        self.assertTrue((app / "Contents/MacOS/UDM Capture").is_file())
        info = plistlib.loads((appex / "Contents/Info.plist").read_bytes())
        self.assertEqual(info["CFBundleIdentifier"], safari.EXTENSION_ID)
        self.assertTrue(info["CFBundleIdentifier"].startswith(safari.APP_ID + "."))
        self.assertEqual(
            info["NSExtension"]["NSExtensionPointIdentifier"], "com.apple.Safari.web-extension"
        )
        self.assertEqual(info["UDMAppPath"], "/Applications/UDM.app")
        self.assertTrue(info["UDMBridgeSocket"].endswith("UDM/bridge.sock"))

    def test_extension_is_signed_before_the_app_then_registered(self):
        app = self._install()
        appex = str(app / "Contents/PlugIns/UDM Capture Extension.appex")
        tools = [(command[0], command[-1]) for command in self.runner.commands]
        self.assertEqual(
            tools, [("codesign", appex), ("codesign", str(app)), ("pluginkit", appex)]
        )

    def test_reinstall_replaces_the_previous_app(self):
        app = self._install()
        (app / "stale").write_text("old")
        self._install()
        self.assertFalse((app / "stale").exists())

    def test_entitlements_allow_only_the_bridge_socket(self):
        rules = safari.extension_entitlements('/tmp/a "b"/bridge.sock')[
            "com.apple.security.temporary-exception.sbpl"
        ]
        self.assertIn('(path-literal "/tmp/a \\"b\\"/bridge.sock")', rules[0])
        self.assertTrue(all("unix-socket" in rule for rule in rules))
        self.assertTrue(safari.sandbox_entitlements()["com.apple.security.app-sandbox"])

    def test_compile_reports_missing_swift(self):
        def runner(command, **kwargs):
            raise FileNotFoundError(command[0])

        with self.assertRaisesRegex(OSError, "xcode-select"):
            safari.compile_binaries(self.root / "bin", runner=runner)

    def test_compile_failure_raises_os_error(self):
        def runner(command, **kwargs):
            return subprocess.CompletedProcess(command, 1, "", "error: no such module")

        with self.assertRaisesRegex(OSError, "no such module"):
            safari.compile_binaries(self.root / "bin", runner=runner)


class SafariInstallerTests(unittest.TestCase):
    def test_install_builds_the_app_without_host_manifests(self):
        browser = browser_by_key("safari")
        with tempfile.TemporaryDirectory() as temp:
            app = Path(temp) / "UDM Capture.app"
            with patch.object(safari, "install", return_value=app) as build:
                result = installer.install(browser, home=temp, data_dir=temp)
        build.assert_called_once()
        self.assertEqual(result.extension_dir, app)
        self.assertEqual(result.host_manifests, ())
        self.assertIn("Allow unsigned extensions", " ".join(result.steps))

    def test_setup_opens_the_extension_app(self):
        result = installer.InstallResult(Path("/x/UDM Capture.app"), None, (), ())
        runner = FakeRunner()
        installer.open_setup_pages(browser_by_key("safari"), result, runner)
        self.assertEqual(runner.commands, [["open", "/x/UDM Capture.app"]])


if __name__ == "__main__":
    unittest.main()
