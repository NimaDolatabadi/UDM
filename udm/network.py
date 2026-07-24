"""HTTP session construction with optional custom DNS resolution."""

import random
import socket
import struct
from urllib.parse import urlsplit, urlunsplit

import requests
from requests.adapters import HTTPAdapter


class DnsResolutionError(requests.RequestException):
    """Report failure to resolve a host through configured DNS servers."""


class CustomDnsResolver:
    """Resolve IPv4 hostnames directly through a configured DNS server."""

    def __init__(self, servers, timeout=3):
        self.servers = [item.strip() for item in servers.split(",") if item.strip()]
        self.timeout = timeout

    def resolve(self, hostname):
        """Return the first IPv4 address reported by a configured server."""
        query_id = random.randrange(0, 65536)
        labels = hostname.encode("idna").split(b".")
        question = b"".join(bytes([len(label)]) + label for label in labels)
        packet = (
            struct.pack("!HHHHHH", query_id, 0x0100, 1, 0, 0, 0)
            + question
            + b"\0"
            + struct.pack("!HH", 1, 1)
        )
        for server in self.servers:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client:
                    client.settimeout(self.timeout)
                    client.sendto(packet, (server, 53))
                    response = client.recv(4096)
                address = self._first_address(response, query_id)
                if address:
                    return address
            except (OSError, ValueError):
                continue
        raise DnsResolutionError(f"Custom DNS could not resolve {hostname}")

    @classmethod
    def _first_address(cls, packet, query_id):
        if len(packet) < 12:
            return None
        received_id, flags, questions, answers = struct.unpack("!HHHH", packet[:8])
        if received_id != query_id or flags & 0x000F:
            return None
        offset = 12
        for _ in range(questions):
            offset = cls._skip_name(packet, offset) + 4
        for _ in range(answers):
            offset = cls._skip_name(packet, offset)
            if offset + 10 > len(packet):
                return None
            record_type, record_class, _, length = struct.unpack(
                "!HHIH", packet[offset : offset + 10]
            )
            offset += 10
            value = packet[offset : offset + length]
            if record_type == 1 and record_class == 1 and len(value) == 4:
                return socket.inet_ntoa(value)
            offset += length
        return None

    @staticmethod
    def _skip_name(packet, offset):
        while offset < len(packet):
            length = packet[offset]
            if length & 0xC0 == 0xC0:
                return offset + 2
            offset += 1
            if length == 0:
                return offset
            offset += length
        raise ValueError("Truncated DNS name")


class CustomDnsAdapter(HTTPAdapter):
    """Route requests to resolved IPs while preserving HTTP host and TLS SNI."""

    def __init__(self, resolver):
        super().__init__()
        self.resolver = resolver

    def send(self, request, **kwargs):
        """Resolve the prepared request URL before delegating transport."""
        parsed = urlsplit(request.url)
        try:
            socket.inet_aton(parsed.hostname or "")
            return super().send(request, **kwargs)
        except OSError:
            pass
        hostname = parsed.hostname
        if not hostname:
            return super().send(request, **kwargs)
        address = self.resolver.resolve(hostname)
        port = f":{parsed.port}" if parsed.port else ""
        request.headers["Host"] = f"{hostname}{port}"
        request.url = urlunsplit(
            (parsed.scheme, f"{address}{port}", parsed.path, parsed.query, parsed.fragment)
        )
        request._udm_tls_hostname = hostname
        return super().send(request, **kwargs)

    def get_connection_with_tls_context(
        self,
        request,
        verify,
        proxies=None,
        cert=None,
    ):
        """Configure certificate hostname and SNI for an IP-address pool."""
        pool = super().get_connection_with_tls_context(
            request,
            verify,
            proxies=proxies,
            cert=cert,
        )
        hostname = getattr(request, "_udm_tls_hostname", None)
        if hostname and request.url.startswith("https://"):
            pool.assert_hostname = hostname
            pool.conn_kw["server_hostname"] = hostname
        return pool


def create_http_session(dns_servers=""):
    """Return a Requests session using configured DNS servers when supplied."""
    session = requests.Session()
    if dns_servers.strip():
        adapter = CustomDnsAdapter(CustomDnsResolver(dns_servers))
        session.mount("http://", adapter)
        session.mount("https://", adapter)
    return session
