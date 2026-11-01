"""Supported browsers and where each one looks for native-messaging hosts.

Each browser lists its locations per platform. Paths are relative to a base
the registration code supplies: ``~/Library/Application Support`` on macOS,
the home folder on Linux, and ``HKEY_CURRENT_USER`` registry keys on Windows.
Some Chromium forks also read Google Chrome's location, so a browser may list
several and the host manifest is written to each.
"""

from dataclasses import dataclass

from udm import paths
from udm.bridge import browser_detect

CHROMIUM = "chromium"
FIREFOX = "firefox"
# Safari loads the extension from an app; see udm.bridge.safari.
SAFARI = "safari"

_CHROME_MAC = "Google/Chrome/NativeMessagingHosts"
_CHROME_LINUX = ".config/google-chrome/NativeMessagingHosts"
_CHROME_KEY = r"Software\Google\Chrome\NativeMessagingHosts"


@dataclass(frozen=True)
class Browser:
    """One browser the extension can be installed into.

    ``mac_apps`` are app bundle names, ``linux_commands`` executable names on
    ``PATH``, and ``windows_exes`` paths below Program Files or Local AppData,
    used to detect an installation. ``*_hosts`` are the native-messaging
    locations described in the module docstring; Safari has none, because it
    reaches UDM through its own app extension. ``store_url`` is the store
    listing, empty until the extension is published there.
    """

    key: str
    name: str
    engine: str
    extensions_url: str
    mac_apps: tuple = ()
    mac_hosts: tuple = ()
    linux_commands: tuple = ()
    linux_hosts: tuple = ()
    windows_exes: tuple = ()
    windows_hosts: tuple = ()
    store_url: str = ""

    def supports(self, platform=None):
        """Return whether the browser exists on ``platform`` (default: this one)."""
        platform = platform or paths.platform_key()
        if platform == paths.DARWIN:
            return bool(self.mac_apps)
        if platform == paths.WINDOWS:
            return bool(self.windows_hosts)
        return bool(self.linux_hosts)

    def host_locations(self, platform=None):
        """Return the native-messaging locations for ``platform``."""
        platform = platform or paths.platform_key()
        return {
            paths.DARWIN: self.mac_hosts,
            paths.WINDOWS: self.windows_hosts,
            paths.LINUX: self.linux_hosts,
        }[platform]

    def app_path(self, platform=None):
        """Return the installed app or executable path, or ``None``."""
        return browser_detect.locate(self, platform)

    def is_installed(self, platform=None):
        """Return whether the browser is installed for the current user."""
        return self.app_path(platform) is not None


BROWSERS = (
    Browser(
        "chrome", "Google Chrome", CHROMIUM, "chrome://extensions",
        mac_apps=("Google Chrome.app",), mac_hosts=(_CHROME_MAC,),
        linux_commands=("google-chrome", "google-chrome-stable"),
        linux_hosts=(_CHROME_LINUX,),
        windows_exes=(r"Google\Chrome\Application\chrome.exe",),
        windows_hosts=(_CHROME_KEY,),
    ),
    Browser(
        "firefox", "Mozilla Firefox", FIREFOX, "about:debugging#/runtime/this-firefox",
        mac_apps=("Firefox.app", "Firefox Developer Edition.app", "Firefox Nightly.app"),
        mac_hosts=("Mozilla/NativeMessagingHosts",),
        linux_commands=("firefox", "firefox-esr"),
        linux_hosts=(".mozilla/native-messaging-hosts",),
        windows_exes=(r"Mozilla Firefox\firefox.exe",),
        windows_hosts=(r"Software\Mozilla\NativeMessagingHosts",),
    ),
    Browser("safari", "Safari", SAFARI, "", mac_apps=("Safari.app",)),
    Browser(
        "edge", "Microsoft Edge", CHROMIUM, "edge://extensions",
        mac_apps=("Microsoft Edge.app",),
        mac_hosts=("Microsoft Edge/NativeMessagingHosts",),
        linux_commands=("microsoft-edge", "microsoft-edge-stable"),
        linux_hosts=(".config/microsoft-edge/NativeMessagingHosts",),
        windows_exes=(r"Microsoft\Edge\Application\msedge.exe",),
        windows_hosts=(r"Software\Microsoft\Edge\NativeMessagingHosts",),
    ),
    Browser(
        "brave", "Brave", CHROMIUM, "brave://extensions",
        mac_apps=("Brave Browser.app",),
        mac_hosts=("BraveSoftware/Brave-Browser/NativeMessagingHosts",),
        linux_commands=("brave-browser", "brave"),
        linux_hosts=(".config/BraveSoftware/Brave-Browser/NativeMessagingHosts",),
        windows_exes=(r"BraveSoftware\Brave-Browser\Application\brave.exe",),
        # NOTE: Brave and Vivaldi builds differ in whether they read their own
        # key or Chrome's on Windows, so both are written.
        windows_hosts=(
            r"Software\BraveSoftware\Brave-Browser\NativeMessagingHosts", _CHROME_KEY,
        ),
    ),
    Browser(
        "vivaldi", "Vivaldi", CHROMIUM, "vivaldi://extensions",
        mac_apps=("Vivaldi.app",), mac_hosts=("Vivaldi/NativeMessagingHosts",),
        linux_commands=("vivaldi", "vivaldi-stable"),
        linux_hosts=(".config/vivaldi/NativeMessagingHosts",),
        windows_exes=(r"Vivaldi\Application\vivaldi.exe",),
        windows_hosts=(r"Software\Vivaldi\NativeMessagingHosts", _CHROME_KEY),
    ),
    # NOTE: Opera and Arc document no host location of their own; writing
    # Chrome's location as well covers the builds that read it.
    Browser(
        "opera", "Opera", CHROMIUM, "opera://extensions",
        mac_apps=("Opera.app",),
        mac_hosts=("com.operasoftware.Opera/NativeMessagingHosts", _CHROME_MAC),
        linux_commands=("opera",), linux_hosts=(_CHROME_LINUX,),
        windows_exes=(r"Programs\Opera\opera.exe", r"Opera\opera.exe"),
        windows_hosts=(_CHROME_KEY,),
    ),
    Browser(
        "arc", "Arc", CHROMIUM, "arc://extensions",
        mac_apps=("Arc.app",),
        mac_hosts=("Arc/User Data/NativeMessagingHosts", _CHROME_MAC),
        windows_hosts=(_CHROME_KEY,),
    ),
    Browser(
        "chromium", "Chromium", CHROMIUM, "chrome://extensions",
        mac_apps=("Chromium.app",), mac_hosts=("Chromium/NativeMessagingHosts",),
        linux_commands=("chromium", "chromium-browser"),
        linux_hosts=(".config/chromium/NativeMessagingHosts",),
        windows_exes=(r"Chromium\Application\chrome.exe",),
        windows_hosts=(r"Software\Chromium\NativeMessagingHosts",),
    ),
)


def supported_browsers(platform=None):
    """Return the browsers that exist on ``platform``, in display order."""
    return tuple(browser for browser in BROWSERS if browser.supports(platform))


def browser_by_key(key):
    """Return the browser with ``key``; raise ``KeyError`` when unknown."""
    for browser in BROWSERS:
        if browser.key == key:
            return browser
    raise KeyError(key)
