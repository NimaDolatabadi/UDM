"""Native-messaging host that relays browser requests to the desktop app.

Browsers start this process (through the wrapper script written by
:mod:`udm.bridge.installer`) for each extension message. It must not import Qt
or write anything except protocol frames to stdout.
"""

import contextlib
import logging
import os
import subprocess
import sys
import time

from udm import __version__, paths
from udm.bridge import connection_status
from udm.capture import CaptureRequest
from udm.bridge.protocol import (
    BridgeError,
    compatibility_error,
    protocol_info,
    read_native_message,
    send_to_app,
    write_native_message,
)

LAUNCH_TIMEOUT = 20.0
_POLL_INTERVAL = 0.25


def run(stdin=None, stdout=None, socket_path=None, launcher=None, prober=None,
        recorder=None):
    """Serve framed messages until the browser closes stdin; return an exit code."""
    stdin = stdin or _standard_stream(sys.stdin, 0, "rb")
    stdout = stdout or _standard_stream(sys.stdout, 1, "wb")
    socket_path = socket_path or paths.bridge_socket_path()
    launcher = launcher or launch_app
    prober = prober or probe_formats
    recorder = recorder or connection_status.record
    while True:
        try:
            message = read_native_message(stdin)
        except BridgeError as error:
            write_native_message(stdout, {"ok": False, "error": str(error)})
            return 1
        if message is None:
            return 0
        recorder(message)
        write_native_message(stdout, handle(message, socket_path, launcher, prober))


def handle(message, socket_path, launcher, prober=None):
    """Return the reply for one extension message."""
    if message.get("type") == "ping":
        try:
            reply = send_to_app(message, socket_path, timeout=2.0)
        except (ConnectionError, OSError, BridgeError):
            # The host ships with UDM, so it speaks for the installed app.
            return {
                "ok": True, "host": True, "running": False,
                "version": __version__, **protocol_info(),
            }
        return {"host": True, **reply}
    problem = compatibility_error(message)
    if problem:
        return {"ok": False, "incompatible": True, "error": problem, **protocol_info()}
    if message.get("type") == "formats":
        return (prober or probe_formats)(message)
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


def launch_app(popen=subprocess.Popen):
    """Start the desktop app detached from the browser's process group."""
    bundle = paths.app_bundle()
    command = ["open", str(bundle)] if bundle else paths.app_command()
    options = dict(
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    if paths.platform_key() != paths.WINDOWS:
        # A new session keeps the app alive after the browser reaps this host.
        popen(command, start_new_session=True, **options)
        return
    detached = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    try:
        # Chrome runs hosts in a job that ends with the host; leave it if allowed.
        popen(command, creationflags=detached | subprocess.CREATE_BREAKAWAY_FROM_JOB,
              **options)
    except OSError:
        popen(command, creationflags=detached, **options)


def _standard_stream(stream, descriptor, mode):
    """Return the binary standard stream, even when Python did not open one.

    Windowed Windows builds may start with ``sys.stdin`` set to ``None`` even
    though the browser passed pipe handles, so fall back to the descriptor.
    """
    if stream is not None:
        return stream.buffer
    return os.fdopen(descriptor, mode, buffering=0)


def main():
    """Entry point used by ``MACDM.py --native-messaging-host``."""
    logging.basicConfig(
        filename=paths.log_file("native-host.log"),
        level=logging.INFO,
    )
    from udm.tls import use_system_trust

    use_system_trust()
    return run()
