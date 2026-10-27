"""Tests for extension assembly and per-browser native-host installation."""

import json
import os
from pathlib import Path
import tempfile
import unittest

from udm.bridge import extension_build, installer
from udm.bridge.browsers import BROWSERS, CHROMIUM, FIREFOX, SAFARI, browser_by_key
from udm.bridge.protocol import NATIVE_HOST_NAME

EXPECTED_CHROMIUM_ID = "himmjkpdagijcljpofjkgoagloapginc"
SCRIPTS = (
    "background.js", "common.js", "downloads.js", "media.js", "overlay.js", "overlay-style.js",
    "popup.css", "popup.html", "popup.js",
)


class ExtensionBuildTests(unittest.TestCase):
    def test_chromium_build_uses_service_worker_key_and_version(self):
        with tempfile.TemporaryDirectory() as temp:
            out = extension_build.build_extension(CHROMIUM, Path(temp) / "ext", "9.8.7")
            manifest = json.loads((out / "manifest.json").read_text())
            for name in SCRIPTS:
                self.assertTrue((out / name).is_file(), name)
            self.assertTrue((out / "icons" / "icon-128.png").is_file())
        self.assertEqual(manifest["version"], "9.8.7")
        self.assertEqual(manifest["background"], {"service_worker": "background.js"})
        self.assertIn("key", manifest)
        self.assertEqual(manifest["content_scripts"][0]["js"], ["overlay-style.js", "overlay.js"])

    def test_firefox_build_uses_background_scripts_and_gecko_id(self):
        with tempfile.TemporaryDirectory() as temp:
            out = extension_build.build_extension(FIREFOX, Path(temp) / "ext", "1.0.0")
            manifest = json.loads((out / "manifest.json").read_text())
        self.assertNotIn("key", manifest)
        self.assertEqual(manifest["background"]["scripts"][-1], "background.js")
        self.assertIn("gecko", manifest["browser_specific_settings"])
        self.assertIn("downloads.js", manifest["background"]["scripts"])
        # Firefox adds blocking webRequest on top of the shared permissions.
        self.assertIn("webRequestBlocking", manifest["permissions"])
        self.assertIn("downloads", manifest["permissions"])

    def test_chromium_build_omits_blocking_web_request(self):
        manifest = extension_build.load_manifest(CHROMIUM)
        self.assertNotIn("webRequestBlocking", manifest["permissions"])
        self.assertIn("downloads", manifest["permissions"])

    def test_rebuild_replaces_stale_files(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "ext"
            out.mkdir()
            (out / "stale.js").write_text("old")
            extension_build.build_extension(CHROMIUM, out, "1.0.0")
            self.assertFalse((out / "stale.js").exists())

    def test_chromium_id_is_derived_from_manifest_key(self):
        self.assertEqual(extension_build.chromium_extension_id(), EXPECTED_CHROMIUM_ID)


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)

    def _install(self, key):
        return installer.install(
            browser_by_key(key),
            home=self.root / "home",
            data_dir=self.root / "data",
            host_command=["/usr/bin/python3", "/opt/udm/MACDM.py"],
        )

    def test_chrome_install_writes_wrapper_manifest_and_extension(self):
        result = self._install("chrome")
        manifest_path = (
            self.root / "home/Library/Application Support/Google/Chrome"
            / "NativeMessagingHosts" / f"{NATIVE_HOST_NAME}.json"
        )
        self.assertEqual(result.host_manifests, (manifest_path,))
        manifest = json.loads(manifest_path.read_text())
        self.assertEqual(manifest["path"], str(result.host_wrapper))
        self.assertEqual(
            manifest["allowed_origins"], [f"chrome-extension://{EXPECTED_CHROMIUM_ID}/"]
        )
        self.assertTrue(os.access(result.host_wrapper, os.X_OK))
        self.assertIn(
            "exec /usr/bin/python3 /opt/udm/MACDM.py --native-messaging-host",
            result.host_wrapper.read_text(),
        )
        self.assertTrue((result.extension_dir / "manifest.json").is_file())
        self.assertIn(str(result.extension_dir), " ".join(result.steps))

    def test_firefox_install_authorizes_gecko_extension(self):
        result = self._install("firefox")
        manifest = json.loads(result.host_manifests[0].read_text())
        self.assertEqual(
            manifest["allowed_extensions"], [extension_build.firefox_extension_id()]
        )
        self.assertIn("Mozilla/NativeMessagingHosts", str(result.host_manifests[0]))
        self.assertIn("Temporary", " ".join(result.steps))

    def test_opera_writes_every_listed_host_directory(self):
        result = self._install("opera")
        self.assertEqual(len(result.host_manifests), 2)

    def test_open_setup_pages_reveals_folder_and_tolerates_failures(self):
        result = self._install("chrome")
        calls = []

        def runner(command, **kwargs):
            calls.append(command)
            raise OSError("no browser")

        installer.open_setup_pages(browser_by_key("chrome"), result, runner)
        self.assertEqual(calls[0][:2], ["open", "-R"])

    def test_every_browser_has_unique_key_and_known_engine(self):
        keys = [browser.key for browser in BROWSERS]
        self.assertEqual(len(keys), len(set(keys)))
        for browser in BROWSERS:
            self.assertIn(browser.engine, (CHROMIUM, FIREFOX, SAFARI))
            # Only Safari reaches UDM without a host manifest.
            self.assertEqual(bool(browser.host_dirs), browser.engine != SAFARI)


if __name__ == "__main__":
    unittest.main()
