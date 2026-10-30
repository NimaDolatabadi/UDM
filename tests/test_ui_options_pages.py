"""Offscreen tests for the Downloads and Network pages and the install prompt."""

from pathlib import Path
import unittest

from tests.qt_support import QtTestCase
from udm.bridge.browsers import browser_by_key
from udm.proxy import PROXY_NONE, PROXY_SOCKS5
from udm.ui.extension_install_dialog import (
    ExtensionInstallDialog,
    install_actions,
    install_target,
)
from udm.ui.options_downloads_page import DownloadsPage
from udm.ui.options_network_page import NetworkPage


class NetworkPageTests(QtTestCase):
    def test_no_proxy_hides_server_fields(self):
        page = NetworkPage({"proxy": "", "dns": ""})
        self.assertEqual(page.proxy_kind.value(), PROXY_NONE)
        self.assertTrue(page.proxy_details.isHidden())
        self.assertEqual(page.values(), {"proxy": "", "dns": ""})

    def test_stored_proxy_fills_fields_and_round_trips(self):
        url = "socks5h://alice:secret@proxy.example.com:1080"
        page = NetworkPage({"proxy": url, "dns": " 1.1.1.1 "})
        self.assertEqual(page.proxy_kind.value(), PROXY_SOCKS5)
        self.assertFalse(page.proxy_details.isHidden())
        self.assertEqual(page.proxy_host.text(), "proxy.example.com")
        self.assertEqual(page.proxy_port.value(), 1080)
        self.assertEqual(page.proxy_username.text(), "alice")
        self.assertEqual(page.values(), {"proxy": url, "dns": "1.1.1.1"})

    def test_switching_type_rebuilds_url_and_none_clears_it(self):
        page = NetworkPage({"proxy": "http://proxy.local:3128"})
        page.proxy_kind.button("socks5").click()
        self.assertEqual(page.values()["proxy"], "socks5h://proxy.local:3128")
        page.proxy_kind.button("none").click()
        self.assertTrue(page.proxy_details.isHidden())
        self.assertEqual(page.values()["proxy"], "")

    def test_unedited_stored_value_is_kept_exactly(self):
        for url in ("socks4://proxy:1080", "http://[::1", "https://u:@proxy:8443"):
            page = NetworkPage({"proxy": url})
            self.assertEqual(page.values()["proxy"], url)

    def test_unsupported_value_selects_no_type_until_chosen(self):
        page = NetworkPage({"proxy": "socks4://proxy:1080"})
        self.assertIsNone(page.proxy_kind.value())
        self.assertIn("can't edit", page.proxy_hint.text())
        page.proxy_kind.button("none").click()
        self.assertEqual(page.values()["proxy"], "")

    def test_editing_keeps_https_scheme_and_username_spaces(self):
        page = NetworkPage({"proxy": "https://alice:pw@proxy:8443"})
        page.proxy_username.setText(" bob ")
        page.proxy_username.textEdited.emit(" bob ")
        self.assertEqual(page.values()["proxy"], "https://%20bob%20:pw@proxy:8443")

    def test_default_port_is_omitted(self):
        page = NetworkPage({"proxy": "http://proxy.local"})
        self.assertEqual(page.proxy_port.text(), "Default")
        page.proxy_kind.button("socks5").click()
        self.assertEqual(page.values()["proxy"], "socks5h://proxy.local")


class DownloadsPageTests(QtTestCase):
    def test_values_round_trip_moved_settings(self):
        config = {
            "download_dir": "/data",
            "stream_quality": "720p",
            "max_concurrent": 3,
            "segments": 12,
            "confirm_new_downloads": False,
            "capture_autostart": True,
            "clipboard_monitor": True,
            "sound_on_complete": True,
        }
        self.assertEqual(DownloadsPage(config).values(), config)

    def test_autostart_is_disabled_while_the_prompt_decides(self):
        page = DownloadsPage({"confirm_new_downloads": True})
        self.assertFalse(page.autostart.isEnabled())
        page.confirm.setChecked(False)
        self.assertTrue(page.autostart.isEnabled())
        self.assertIn("paused", page.autostart_hint.text())


class InstallDialogTests(QtTestCase):
    def test_actions_describe_each_engine(self):
        self.assertIn("Finder", install_actions(browser_by_key("chrome"))[-1])
        self.assertIn("add-ons", install_actions(browser_by_key("firefox"))[-1])
        self.assertIn("Safari", install_actions(browser_by_key("safari"))[-1])

    def test_target_matches_installer_layout(self):
        data = Path("/data")
        self.assertEqual(
            install_target(browser_by_key("brave"), data), data / "extension" / "chromium"
        )
        self.assertEqual(install_target(browser_by_key("safari"), data), data / "safari")

    def test_dialog_lists_actions_and_defaults_to_install(self):
        dialog = ExtensionInstallDialog(browser_by_key("firefox"), data_dir="/data")
        self.assertEqual(len(dialog.actions), 3)
        self.assertTrue(dialog.install_button.isDefault())
        dialog.close()


if __name__ == "__main__":
    unittest.main()
