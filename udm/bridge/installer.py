"""Developer installation of the extension from this copy of UDM.

Browsers do not let applications add extensions silently, so installation
prepares everything the browser needs and then guides the user through the
remaining manual step: loading the unpacked extension folder, or turning the
extension on in Safari's settings.
"""

from dataclasses import dataclass
from pathlib import Path

from udm import __version__, paths
from udm.bridge import browser_detect, extension_build, host_registration, safari
from udm.bridge.browsers import FIREFOX, SAFARI


@dataclass(frozen=True)
class InstallResult:
    """Paths written by an installation and the remaining manual steps.

    For Safari, ``extension_dir`` is ``UDM Capture.app`` and there is no host
    wrapper or host manifest.
    """

    extension_dir: Path
    host_wrapper: Path
    host_manifests: tuple
    steps: tuple


def install(browser, home=None, data_dir=None, host_command=None, source=None,
            platform=None, winreg_module=None):
    """Build the extension from source for ``browser`` and register its host.

    This is the developer install; end users get the extension from a store
    or a release file, and UDM registers the host on launch
    (:func:`udm.bridge.host_registration.sync_all`).
    """
    data_dir = Path(data_dir or paths.data_dir())
    if browser.engine == SAFARI:
        app = safari.install(
            data_dir, __version__, paths.bridge_socket_path(), paths.app_bundle(), source
        )
        return InstallResult(app, None, (), setup_steps(browser, app))
    extension_dir = extension_build.build_extension(
        browser.engine,
        data_dir / "extension" / browser.engine,
        __version__,
        source,
    )
    registration = host_registration.register(
        browser, home, data_dir, host_command, platform, source, winreg_module
    )
    return InstallResult(
        extension_dir,
        registration.wrapper,
        registration.manifests,
        setup_steps(browser, extension_dir),
    )


def setup_steps(browser, extension_dir):
    """Return the manual steps that finish installation in ``browser``."""
    if browser.engine == SAFARI:
        return (
            "In Safari, choose Safari > Settings > Advanced and turn on "
            '"Show features for web developers".',
            'In the Developer tab, turn on "Allow unsigned extensions". Safari '
            "turns this off when it quits; turn it on again after restarting "
            "Safari.",
            "In the Extensions tab, turn on UDM Capture, then click Edit "
            'Websites and choose Allow for "Other websites".',
            "After updating UDM, install again.",
        )
    if browser.engine == FIREFOX:
        return (
            f"Open {browser.extensions_url} in Firefox.",
            'Click "Load Temporary Add-on..." and choose '
            f"{extension_dir / 'manifest.json'}.",
            "Firefox removes temporary add-ons when it quits; repeat these "
            "steps after restarting Firefox until the add-on is signed.",
        )
    return (
        f"Open {browser.extensions_url} in {browser.name}.",
        "Turn on Developer mode.",
        f'Click "Load unpacked" and choose {extension_dir}.',
        "Pin UDM Capture to the toolbar. After updating UDM, install again "
        "and click Reload on the extension card.",
    )


def open_setup_pages(browser, result, runner=None, platform=None):
    """Reveal the extension folder and open the browser's extensions page.

    For Safari, opening ``UDM Capture.app`` registers the extension and shows
    it in Safari's settings. Failures are ignored, because the written steps
    still explain where to go.
    """
    if browser.engine == SAFARI:
        commands = [["open", str(result.extension_dir)]]
    else:
        commands = [browser_detect.reveal_command(
            result.extension_dir / "manifest.json", platform
        )]
        app = browser.app_path(platform)
        if app is not None:
            commands.append(
                browser_detect.open_url_command(app, browser.extensions_url, platform)
            )
    browser_detect.run_quietly(commands, runner or browser_detect.spawn)
