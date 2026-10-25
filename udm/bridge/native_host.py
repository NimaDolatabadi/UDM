"""Native-messaging host that relays browser requests to the desktop app.

Browsers start this process (through the wrapper script written by
:mod:`udm.bridge.installer`) for each extension message. It must not import Qt
or write anything except protocol frames to stdout.
"""

import contextlib
import logging
import subprocess
import sys
import time

from udm import paths
from udm.capture import CaptureRequest
from udm.bridge.protocol import (
    BridgeError,
    read_native_message,
    send_to_app,
    write_native_message,
)

LAUNCH_TIMEOUT = 20.0
_POLL_INTERVAL = 0.25


def run(stdin=None, stdout=None, socket_path=None, launcher=None, prober=None):
    """Serve framed messages until the browser closes stdin; return an exit code."""
    stdin = stdin or sys.stdin.buffer
    stdout = stdout or sys.stdout.buffer
    socket_path = socket_path or paths.bridge_socket_path()
    launcher = launcher or launch_app
    prober = prober or probe_formats
    while True:
        try:
            message = read_native_message(stdin)
        except BridgeError as error:
            write_native_message(stdout, {"ok": False, "error": str(error)})
            return 1
        if message is None:
            return 0
        write_native_message(stdout, handle(message, socket_path, launcher, prober))


def handle(message, socket_path, launcher, prober=None):
    """Return the reply for one extension message."""
    if message.get("type") == "formats":
        return (prober or probe_formats)(message)
    if message.get("type") == "ping":
        try:
            reply = send_to_app(message, socket_path, timeout=2.0)
        except (ConnectionError, OSError, BridgeError):
            return {"ok": True, "host": True, "running": False}
        return {"host": True, **reply}
    try:
        return _forward(message, socket_path, launcher)
    except (ConnectionError, OSError, BridgeError) as error:
        logging.error("Native host could not reach UDM: %s", error)
        return {"ok": False, "error": "UDM is not running and could not start"}


def _forward(message, socket_path, launcher):
    try:
        return send_to_app(message, socket_path)
    except (ConnectionError, OSError):
        pass
    launcher()
    deadline = time.monotonic() + LAUNCH_TIMEOUT
    while True:
        try:
            return send_to_app(message, socket_path)
        except (ConnectionError, OSError):
            if time.monotonic() >= deadline:
                raise
            time.sleep(_POLL_INTERVAL)


def probe_formats(message):
    """Answer a quality request in this process, without the desktop app."""
    try:
        request = CaptureRequest.from_message(message)
    except ValueError as error:
        return {"ok": False, "error": str(error)}
    from udm.config import ConfigManager
    from udm.workers.format_probe import probe_qualities

    proxy = ConfigManager().config.get("proxy", "").strip() or None
    # Stdout carries protocol frames; divert any stray library output.
    with contextlib.redirect_stdout(sys.stderr):
        return probe_qualities(request, proxy=proxy)


def launch_app():
    """Start the desktop app detached from the browser's process group."""
    bundle = paths.app_bundle()
    command = ["open", str(bundle)] if bundle else paths.app_command()
    # A new session keeps the app alive after the browser reaps this host.
    subprocess.Popen(
        command,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def main():
    """Entry point used by ``MACDM.py --native-messaging-host``."""
    logging.basicConfig(
        filename=paths.log_file("native-host.log"),
        level=logging.INFO,
    )
    from udm.tls import use_system_trust

    use_system_trust()
    return run()
