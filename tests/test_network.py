"""Tests for custom DNS-backed HTTP session construction."""

import unittest

from udm.network import CustomDnsAdapter, create_http_session


class NetworkTests(unittest.TestCase):
    def test_custom_dns_mounts_adapter_for_http_and_https(self):
        session = create_http_session("8.8.8.8, 1.1.1.1")
        self.assertIsInstance(session.adapters["http://"], CustomDnsAdapter)
        self.assertIsInstance(session.adapters["https://"], CustomDnsAdapter)
        self.assertEqual(
            session.adapters["https://"].resolver.servers,
            ["8.8.8.8", "1.1.1.1"],
        )

    def test_blank_dns_uses_default_requests_adapters(self):
        session = create_http_session(" ")
        self.assertNotIsInstance(session.adapters["https://"], CustomDnsAdapter)


if __name__ == "__main__":
    unittest.main()
