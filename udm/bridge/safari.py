"""Assemble the Safari app that carries the UDM Capture web extension.

Safari loads web extensions only from an app extension inside a containing
app, and routes native messages to that app extension instead of a host
manifest. Installation therefore writes ``UDM Capture.app``: the web extension
files, the Swift handler from ``extension/safari/`` (which relays messages to
the bridge socket), Info.plists, and sandbox entitlements, ad hoc signed and
registered with PlugInKit.

Release builds ship the compiled Swift binaries (``build_dmg.sh``); source
runs compile them with the Xcode Command Line Tools.
"""

import os
from pathlib import Path
import platform
import plistlib
import shutil
import subprocess

from udm import paths
from udm.bridge import extension_build
from udm.bridge.browsers import SAFARI

APP_NAME = "UDM Capture.app"
APP_ID = "com.udm.manager.safari"
EXTENSION_ID = f"{APP_ID}.extension"
APP_EXECUTABLE = "UDM Capture"
EXTENSION_EXECUTABLE = "UDMCaptureExtension"
MIN_MACOS = "12.0"
BINARY_DIR = "safari-bin"


def install(data_dir, version, socket_path, app_bundle=None, source=None,
            binaries=None, runner=subprocess.run):
    """Write and sign ``UDM Capture.app`` in ``data_dir``; return its path.

    ``app_bundle`` is the UDM app the extension starts when UDM is closed.
    ``binaries`` maps ``"app"`` and ``"extension"`` to compiled executables;
    by default the bundled ones are used, or compiled from source.
    """
    safari_dir = Path(data_dir) / "safari"
    binaries = binaries or bundled_binaries() or compile_binaries(
        safari_dir / "bin", source, runner
    )
    app = safari_dir / APP_NAME
    if app.exists():
        shutil.rmtree(app)
    appex = app / "Contents" / "PlugIns" / "UDM Capture Extension.appex"
    extension_build.build_extension(
        SAFARI, appex / "Contents" / "Resources", version, source
    )
    _place(binaries["extension"], appex / "Contents" / "MacOS" / EXTENSION_EXECUTABLE)
    _place(binaries["app"], app / "Contents" / "MacOS" / APP_EXECUTABLE)
    _write_plist(appex / "Contents" / "Info.plist", extension_info(
        version, socket_path, app_bundle
    ))
    _write_plist(app / "Contents" / "Info.plist", app_info(version))
    entitlements = safari_dir / "entitlements"
    entitlements.mkdir(exist_ok=True)
    _write_plist(entitlements / "extension.plist", extension_entitlements(socket_path))
    _write_plist(entitlements / "app.plist", sandbox_entitlements())
    # The app extension is signed first; signing the app seals it in.
    _sign(appex, entitlements / "extension.plist", runner)
    _sign(app, entitlements / "app.plist", runner)
    # Safari lists only registered app extensions.
    _run(["pluginkit", "-a", str(appex)], runner, timeout=30,
         missing="pluginkit is not available")
    return app


def bundled_binaries():
    """Return the executables shipped with a release build, or ``None``."""
    folder = paths.resource_path(BINARY_DIR)
    found = {"app": folder / "app", "extension": folder / "extension"}
    return found if all(path.is_file() for path in found.values()) else None


def compile_binaries(destination, source=None, runner=subprocess.run):
    """Compile the Swift app and app extension into ``destination``.

    Raises ``OSError`` when the Swift compiler is missing or fails.
    """
    swift = Path(source or extension_build.source_dir()) / "safari"
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    target = f"{platform.machine()}-apple-macos{MIN_MACOS}"
    common = ["xcrun", "swiftc", "-swift-version", "5", "-O", "-target", target]
    commands = {
        "extension": common + [
            "-module-name", EXTENSION_EXECUTABLE, "-parse-as-library",
            "-application-extension", "-Xlinker", "-e", "-Xlinker", "_NSExtensionMain",
            "-framework", "SafariServices", "-framework", "AppKit",
            str(swift / "SafariWebExtensionHandler.swift"),
        ],
        "app": common + [
            "-module-name", "UDMCapture", "-framework", "SafariServices",
            str(swift / "ContainerApp.swift"),
        ],
    }
    built = {}
    for name, command in commands.items():
        built[name] = destination / name
        _run(command + ["-o", str(built[name])], runner, timeout=300,
             missing="Safari support needs the Swift compiler. Install the "
                     "Xcode Command Line Tools with: xcode-select --install")
    return built


def extension_info(version, socket_path, app_bundle=None):
    """Return the app extension's Info.plist, including the bridge settings."""
    return {
        **_bundle_info(EXTENSION_ID, EXTENSION_EXECUTABLE, "XPC!", version),
        "CFBundleName": "UDM Capture Extension",
        "CFBundleDisplayName": "UDM Capture",
        "NSExtension": {
            "NSExtensionPointIdentifier": "com.apple.Safari.web-extension",
            "NSExtensionPrincipalClass": "SafariWebExtensionHandler",
        },
        "UDMBridgeSocket": str(socket_path),
        "UDMAppPath": str(app_bundle or ""),
    }


def app_info(version):
    """Return the containing app's Info.plist."""
    return {
        **_bundle_info(APP_ID, APP_EXECUTABLE, "APPL", version),
        "CFBundleName": "UDM Capture",
        # The app only opens Safari's settings, so it stays out of the Dock.
        "LSUIElement": True,
    }


def sandbox_entitlements():
    """Return the App Sandbox entitlements Safari requires."""
    return {"com.apple.security.app-sandbox": True}


def extension_entitlements(socket_path):
    """Return sandbox entitlements that allow connecting to the bridge socket.

    The App Sandbox blocks Unix-socket connections outside the container, and
    no standard entitlement grants one, so a sandbox-profile exception names
    the socket. Both the given path and its resolved form are listed, because
    temporary directories sit behind the ``/var`` symlink.
    """
    socket_path = Path(socket_path)
    candidates = dict.fromkeys(
        [str(socket_path), os.path.join(os.path.realpath(socket_path.parent), socket_path.name)]
    )
    rules = [
        f"(allow network-outbound (remote unix-socket (path-literal {_sbpl_string(path)})))"
        for path in candidates
    ]
    return {
        **sandbox_entitlements(),
        "com.apple.security.temporary-exception.sbpl": rules,
    }


def _bundle_info(identifier, executable, package_type, version):
    return {
        "CFBundleIdentifier": identifier,
        "CFBundleExecutable": executable,
        "CFBundlePackageType": package_type,
        "CFBundleInfoDictionaryVersion": "6.0",
        "CFBundleShortVersionString": version,
        "CFBundleVersion": version,
        "LSMinimumSystemVersion": MIN_MACOS,
    }


def _sbpl_string(text):
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _place(executable, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(executable, target)
    target.chmod(0o755)


def _write_plist(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as handle:
        plistlib.dump(data, handle)


def _sign(bundle, entitlements, runner):
    _run(
        ["codesign", "--force", "--sign", "-", "--entitlements", str(entitlements),
         str(bundle)],
        runner,
        timeout=60,
        missing="codesign is not available",
    )


def _run(command, runner, timeout, missing):
    try:
        result = runner(command, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError as error:
        raise OSError(missing) from error
    except subprocess.SubprocessError as error:
        raise OSError(f"{command[0]} failed: {error}") from error
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip().splitlines()
        raise OSError(f"{' '.join(command[:2])} failed: {detail[-1] if detail else result.returncode}")
