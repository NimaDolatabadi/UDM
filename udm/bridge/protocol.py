"""Wire formats shared by the extension, native host, and desktop app.

Two transports exist. Browsers talk to the native host over stdio using the
WebExtension native-messaging framing (a 32-bit native-endian length followed
by UTF-8 JSON). The native host talks to the running app over a Unix domain
socket (a named pipe on Windows) using one JSON object per line in each
direction.

``PROTOCOL_VERSION`` describes the message formats, independently of the app
version. Each side sends its version and the oldest peer version it accepts;
messages without one come from releases before versioning, which speak
version 1.
"""

import json
import socket
import struct
import threading

from udm.paths import PIPE_PREFIX

NATIVE_HOST_NAME = "com.udm.capture"
# NOTE: Bump PROTOCOL_VERSION when a message changes shape, and raise
# MIN_PROTOCOL_VERSION only when older extensions can no longer be served.
# Keep both in step with extension/src/common.js.
PROTOCOL_VERSION = 1
MIN_PROTOCOL_VERSION = 1
# Browsers cap host replies at 1 MB; inbound messages are bounded defensively.
MAX_MESSAGE_BYTES = 8 * 1024 * 1024
_LENGTH = struct.Struct("=I")


class BridgeError(Exception):
    """Report a malformed or oversized bridge message."""


def read_native_message(stream):
    """Read one framed message from ``stream``; return ``None`` at end of input."""
    header = stream.read(_LENGTH.size)
    if not header:
        return None
    if len(header) != _LENGTH.size:
        raise BridgeError("Truncated message header")
    (length,) = _LENGTH.unpack(header)
    if length > MAX_MESSAGE_BYTES:
        raise BridgeError(f"Message of {length} bytes exceeds the limit")
    payload = stream.read(length)
    if len(payload) != length:
        raise BridgeError("Truncated message body")
    return _decode(payload)


def write_native_message(stream, message):
    """Write one framed message to ``stream`` and flush it."""
    payload = json.dumps(message, ensure_ascii=False).encode("utf-8")
    stream.write(_LENGTH.pack(len(payload)) + payload)
    stream.flush()


def protocol_info():
    """Return the protocol fields every reply to the extension carries."""
    return {"protocol": PROTOCOL_VERSION, "minProtocol": MIN_PROTOCOL_VERSION}


def compatibility_error(message):
    """Return why UDM cannot serve ``message``'s sender, or ``None``.

    The text tells the user which side to update.
    """
    theirs = _version_field(message, "protocol")
    their_minimum = _version_field(message, "minProtocol")
    if theirs < MIN_PROTOCOL_VERSION:
        return "This UDM Capture extension is too old for UDM. Update the extension."
    if their_minimum > PROTOCOL_VERSION:
        return "This UDM Capture extension needs a newer UDM. Update UDM."
    return None


def encode_line(message):
    """Return ``message`` as one newline-terminated JSON line."""
    return json.dumps(message, ensure_ascii=False).encode("utf-8") + b"\n"


def decode_line(line):
    """Parse one JSON line into a dictionary."""
    return _decode(line.strip())


def send_to_app(message, socket_path, timeout=5.0):
    """Send ``message`` to the running app and return its reply.

    Raises ``ConnectionError`` (including ``FileNotFoundError`` and
    ``ConnectionRefusedError``) when no app is listening, and
    ``BridgeError`` when the reply is malformed.
    """
    if str(socket_path).startswith(PIPE_PREFIX):
        return exchange_over_pipe(message, str(socket_path), timeout)
    if not hasattr(socket, "AF_UNIX"):
        raise ConnectionError("Local sockets are not supported on this platform")
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(timeout)
        try:
            client.connect(str(socket_path))
        except (FileNotFoundError, socket.timeout) as error:
            raise ConnectionError(str(error)) from error
        client.sendall(encode_line(message))
        buffer = b""
        while b"\n" not in buffer:
            chunk = client.recv(65536)
            if not chunk:
                break
            buffer += chunk
            if len(buffer) > MAX_MESSAGE_BYTES:
                raise BridgeError("Reply exceeds the limit")
    if not buffer.strip():
        raise BridgeError("Empty reply from application")
    return decode_line(buffer.split(b"\n", 1)[0])


def exchange_over_pipe(message, pipe_path, timeout=5.0, opener=open):
    """Send ``message`` over a Windows named pipe and return the reply.

    Pipe reads cannot time out, so the exchange runs on a daemon thread and is
    abandoned after ``timeout`` seconds. Raises like :func:`send_to_app`.
    """
    outcome = {}

    def exchange():
        try:
            with opener(pipe_path, "r+b", buffering=0) as pipe:
                pipe.write(encode_line(message))
                buffer = b""
                while b"\n" not in buffer:
                    chunk = pipe.read(65536)
                    if not chunk:
                        break
                    buffer += chunk
                    if len(buffer) > MAX_MESSAGE_BYTES:
                        raise BridgeError("Reply exceeds the limit")
            outcome["reply"] = buffer
        except (OSError, BridgeError) as error:
            outcome["error"] = error

    worker = threading.Thread(target=exchange, daemon=True)
    worker.start()
    worker.join(timeout)
    if worker.is_alive():
        raise ConnectionError("UDM did not answer in time")
    error = outcome.get("error")
    if isinstance(error, BridgeError):
        raise error
    if error is not None:
        # A missing or busy pipe means no app is ready to answer.
        raise ConnectionError(str(error)) from error
    if not outcome["reply"].strip():
        raise BridgeError("Empty reply from application")
    return decode_line(outcome["reply"].split(b"\n", 1)[0])


def _version_field(message, name):
    value = message.get(name, 1)
    return value if isinstance(value, int) and not isinstance(value, bool) else 1


def _decode(payload):
    try:
        message = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as error:
        raise BridgeError(f"Invalid JSON: {error}") from error
    if not isinstance(message, dict):
        raise BridgeError("Message must be a JSON object")
    return message
