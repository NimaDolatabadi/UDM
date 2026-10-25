"""Supported browsers and their macOS native-messaging locations."""

from dataclasses import dataclass
from pathlib import Path

CHROMIUM = "chromium"
FIREFOX = "firefox"


@dataclass(frozen=True)
class Browser:
    """One browser the extension can be installed into.

    ``host_dirs`` are relative to ``~/Library/Application Support``. Some
    Chromium forks also read Google Chrome's directory, so a browser may list
    several and the installer writes the host manifest to each.
    """

    key: str
    name: str
    engine: str
    app_names: tuple
    host_dirs: tuple
    extensions_url: str

    def is_installed(self, roots=None):
        """Return whether the browser app exists in an Applications folder."""
        roots = roots or (Path("/Applications"), Path.home() / "Applications")
        return any((root / app).exists() for root in roots for app in self.app_names)

    def app_path(self, roots=None):
        """Return the installed app bundle path, or ``None``."""
        roots = roots or (Path("/Applications"), Path.home() / "Applications")
        for root in roots:
            for app in self.app_names:
                if (root / app).exists():
                    return root / app
        return None


BROWSERS = (
    Browser(
        "chrome", "Google Chrome", CHROMIUM, ("Google Chrome.app",),
        ("Google/Chrome/NativeMessagingHosts",), "chrome://extensions",
    ),
    Browser(
        "firefox", "Mozilla Firefox", FIREFOX,
        ("Firefox.app", "Firefox Developer Edition.app", "Firefox Nightly.app"),
        ("Mozilla/NativeMessagingHosts",), "about:debugging#/runtime/this-firefox",
    ),
    Browser(
        "edge", "Microsoft Edge", CHROMIUM, ("Microsoft Edge.app",),
        ("Microsoft Edge/NativeMessagingHosts",), "edge://extensions",
    ),
    Browser(
        "brave", "Brave", CHROMIUM, ("Brave Browser.app",),
        ("BraveSoftware/Brave-Browser/NativeMessagingHosts",), "brave://extensions",
    ),
    Browser(
        "vivaldi", "Vivaldi", CHROMIUM, ("Vivaldi.app",),
        ("Vivaldi/NativeMessagingHosts",), "vivaldi://extensions",
    ),
    # NOTE: Opera and Arc document no host directory of their own on macOS;
    # writing Chrome's location as well covers the builds that read it.
    Browser(
        "opera", "Opera", CHROMIUM, ("Opera.app",),
        (
            "com.operasoftware.Opera/NativeMessagingHosts",
            "Google/Chrome/NativeMessagingHosts",
        ),
        "opera://extensions",
    ),
    Browser(
        "arc", "Arc", CHROMIUM, ("Arc.app",),
        ("Arc/User Data/NativeMessagingHosts", "Google/Chrome/NativeMessagingHosts"),
        "arc://extensions",
    ),
    Browser(
        "chromium", "Chromium", CHROMIUM, ("Chromium.app",),
        ("Chromium/NativeMessagingHosts",), "chrome://extensions",
    ),
)


def browser_by_key(key):
    """Return the browser with ``key``; raise ``KeyError`` when unknown."""
    for browser in BROWSERS:
        if browser.key == key:
            return browser
    raise KeyError(key)
