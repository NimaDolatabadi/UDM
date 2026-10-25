"""Wire formats shared by the extension, native host, and desktop app.

Two transports exist. Browsers talk to the native host over stdio using the
WebExtension native-messaging framing (a 32-bit native-endian length followed
by UTF-8 JSON). The native host talks to the running app over a Unix domain
socket using one JSON object per line in each direction.
"""

import json
import socket
import struct

NATIVE_HOST_NAME = "com.udm.capture"
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
    # Windows Python has no AF_UNIX; the bridge is unavailable there.
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


def _decode(payload):
    try:
        message = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as error:
        raise BridgeError(f"Invalid JSON: {error}") from error
    if not isinstance(message, dict):
        raise BridgeError("Message must be a JSON object")
    return message
