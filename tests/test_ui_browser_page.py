"""Offscreen tests for the Browser options page."""

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

from tests.qt_support import QtTestCase
from udm.bridge.browsers import browser_by_key
from udm.bridge.installer import InstallResult
from udm.constants import RELEASES_URL
from udm.ui.options_browser_page import BrowserIntegrationPage, connection_text


def recent(minutes):
    """Return a contact timestamp ``minutes`` ago."""
    moment = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    return moment.isoformat(timespec="seconds")


class BrowserPageTests(QtTestCase):
    def test_install_asks_first_then_reports_steps(self):
        calls = []
        result = InstallResult(Path("/tmp/ext"), Path("/tmp/host"), (), ("Step one.",))

        def fake_install(browser):
            calls.append(browser.key)
            return result

        def confirm(browser, parent):
            calls.append(f"confirm {browser.key}")
            return True

        page = BrowserIntegrationPage(
            {},
            install=fake_install,
            open_pages=lambda browser, res: calls.append("opened"),
            confirm=confirm,
        )
        index = page.browser.findData(browser_by_key("firefox"))
        page.browser.setCurrentIndex(index)
        with patch("udm.ui.options_browser_page.QMessageBox.information") as info:
            self.assertIs(page.install_selected(), result)
        info.assert_called_once()
        self.assertEqual(calls, ["confirm firefox", "firefox", "opened"])
        self.assertIn("1. Step one.", page.status.text())

    def test_declining_the_confirmation_installs_nothing(self):
        calls = []
        page = BrowserIntegrationPage(
            {},
            install=lambda browser: calls.append("installed"),
            open_pages=lambda browser, res: calls.append("opened"),
            confirm=lambda browser, parent: False,
        )
        with patch("udm.ui.options_browser_page.QMessageBox.information") as info:
            self.assertIsNone(page.install_selected())
        info.assert_not_called()
        self.assertEqual(calls, [])

    def test_install_failure_is_shown_without_dialog(self):
        def failing_install(browser):
            raise OSError("read-only")

        page = BrowserIntegrationPage(
            {}, install=failing_install, open_pages=None,
            confirm=lambda browser, parent: True,
        )
        with patch("udm.ui.options_browser_page.QMessageBox.information") as info:
            self.assertIsNone(page.install_selected())
        info.assert_not_called()
        self.assertIn("read-only", page.status.text())


class GetExtensionTests(QtTestCase):
    def _page(self, key, status=None, opened=None, **options):
        page = BrowserIntegrationPage(
            {}, open_url=(opened.append if opened is not None else None),
            load_status=lambda: status or {}, **options,
        )
        page.browser.setCurrentIndex(page.browser.findData(browser_by_key(key)))
        return page

    def test_status_reports_missing_and_recorded_contacts(self):
        page = self._page("firefox")
        self.assertIn("Not connected yet", page.connection.text())
        self.assertEqual(page.connection.property("tone"), "")
        page = self._page("firefox", {"firefox": {"version": "1.2.3", "seen": recent(5)}})
        self.assertIn("UDM Capture 1.2.3 last connected 5 minutes ago", page.connection.text())
        self.assertEqual(page.connection.property("tone"), "success")

    def test_chromium_contacts_are_not_attributed_to_one_browser(self):
        text, connected = connection_text(
            browser_by_key("edge"), {"chromium": {"version": "1", "seen": recent(0)}}
        )
        self.assertTrue(connected)
        self.assertTrue(text.startswith("In a Chromium-based browser"))

    def test_check_again_rereads_the_status(self):
        status = {}
        page = BrowserIntegrationPage({}, load_status=lambda: status)
        page.browser.setCurrentIndex(page.browser.findData(browser_by_key("chrome")))
        status["chromium"] = {"version": "2.0.0", "seen": recent(0)}
        page.check_button.click()
        self.assertIn("just now", page.connection.text())

    def test_get_opens_the_release_page_until_a_store_listing_exists(self):
        opened = []
        page = self._page("chrome", opened=opened)
        page.get_extension()
        self.assertEqual(opened, [RELEASES_URL])
        self.assertIn("not in browser stores yet", page.get_note.text())
        self.assertFalse(page.install_row.isHidden())

    @unittest.skipUnless(sys.platform == "darwin", "Safari exists only on macOS")
    def test_safari_get_runs_the_confirmed_install(self):
        calls = []
        page = self._page(
            "safari", opened=[], confirm=lambda browser, parent: calls.append("asked"),
        )
        self.assertEqual(page.get_button.text(), "Install for Safari...")
        self.assertTrue(page.install_row.isHidden())
        self.assertIsNone(page.get_extension())
        self.assertEqual(calls, ["asked"])


if __name__ == "__main__":
    unittest.main()
