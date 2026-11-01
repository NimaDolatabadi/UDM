"""Tests for per-platform browser detection, commands, and bridge paths."""

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from udm import paths
from udm.bridge import browser_detect
from udm.bridge.browsers import BROWSERS, SAFARI, browser_by_key, supported_browsers


class DetectionTests(unittest.TestCase):
    def test_platform_keys(self):
        self.assertEqual(paths.platform_key("darwin"), paths.DARWIN)
        self.assertEqual(paths.platform_key("win32"), paths.WINDOWS)
        self.assertEqual(paths.platform_key("linux"), paths.LINUX)
        self.assertEqual(paths.platform_key("freebsd14"), paths.LINUX)

    def test_linux_detects_commands_on_path(self):
        found = {"firefox-esr": "/usr/bin/firefox-esr"}
        located = browser_detect.locate(
            browser_by_key("firefox"), paths.LINUX, which=found.get
        )
        self.assertEqual(located, Path("/usr/bin/firefox-esr"))
        self.assertIsNone(
            browser_detect.locate(browser_by_key("chrome"), paths.LINUX, which=found.get)
        )

    def test_windows_detects_executables_below_install_roots(self):
        with tempfile.TemporaryDirectory() as temp:
            exe = Path(temp) / "Microsoft" / "Edge" / "Application" / "msedge.exe"
            exe.parent.mkdir(parents=True)
            exe.write_text("")
            located = browser_detect.locate(
                browser_by_key("edge"), paths.WINDOWS, roots=(temp,)
            )
        self.assertEqual(located, exe)

    def test_windows_roots_skip_missing_variables(self):
        roots = browser_detect.windows_roots({"LOCALAPPDATA": r"C:\Users\u\AppData\Local"})
        self.assertEqual(roots, (Path(r"C:\Users\u\AppData\Local"),))

    def test_safari_exists_only_on_macos(self):
        for platform in (paths.LINUX, paths.WINDOWS):
            engines = {browser.engine for browser in supported_browsers(platform)}
            self.assertNotIn(SAFARI, engines)
        self.assertEqual(len(supported_browsers(paths.DARWIN)), len(BROWSERS))

    def test_every_non_safari_browser_has_hosts_where_supported(self):
        for platform in (paths.DARWIN, paths.LINUX, paths.WINDOWS):
            for browser in supported_browsers(platform):
                if browser.engine != SAFARI:
                    self.assertTrue(browser.host_locations(platform), browser.key)


class CommandTests(unittest.TestCase):
    def test_reveal_uses_each_platforms_file_manager(self):
        target = Path("/data/ext/manifest.json")
        self.assertEqual(browser_detect.reveal_command(target, paths.DARWIN)[:2], ["open", "-R"])
        self.assertEqual(
            browser_detect.reveal_command(target, paths.WINDOWS),
            ["explorer", f"/select,{target}"],
        )
        self.assertEqual(
            browser_detect.reveal_command(target, paths.LINUX), ["xdg-open", "/data/ext"]
        )

    def test_open_url_starts_the_browser_itself_off_macos(self):
        app = Path("/usr/bin/firefox")
        self.assertEqual(
            browser_detect.open_url_command(app, "about:addons", paths.LINUX),
            ["/usr/bin/firefox", "about:addons"],
        )

    def test_run_quietly_ignores_failures(self):
        calls = []

        def runner(command):
            calls.append(command)
            raise OSError("missing")

        browser_detect.run_quietly([["a"], ["b"]], runner)
        self.assertEqual(calls, [["a"], ["b"]])


class SocketPathTests(unittest.TestCase):
    def test_windows_uses_a_named_pipe(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.dict(os.environ, {"UDM_DATA_DIR": temp}), \
                    patch.object(paths, "platform_key", return_value=paths.WINDOWS):
                path = paths.bridge_socket_path()
        self.assertTrue(path.startswith(paths.PIPE_PREFIX))
        self.assertNotIn("\\", path[len(paths.PIPE_PREFIX):])


if __name__ == "__main__":
    unittest.main()
