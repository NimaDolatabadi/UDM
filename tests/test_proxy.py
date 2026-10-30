"""Tests for converting proxy settings to and from a proxy URL."""

import unittest

from udm.proxy import (
    PROXY_HTTP,
    PROXY_NONE,
    PROXY_SOCKS5,
    ProxySettings,
    build_proxy_url,
    is_supported_proxy_url,
    parse_proxy_url,
    split_server,
)


class ProxyUrlTests(unittest.TestCase):
    def test_empty_and_unsupported_values_mean_no_proxy(self):
        for value in ("", "   ", "ftp://proxy:21", "http://proxy:notaport", "http://"):
            self.assertEqual(parse_proxy_url(value).kind, PROXY_NONE, value)

    def test_legacy_value_without_scheme_is_http(self):
        settings = parse_proxy_url("proxy.local:3128")
        self.assertEqual(settings, ProxySettings(PROXY_HTTP, "proxy.local", 3128, scheme="http"))

    def test_socks5_round_trips_with_encoded_credentials(self):
        settings = ProxySettings(PROXY_SOCKS5, "proxy.example.com", 1080, "alice", "p@ss:w/rd")
        url = build_proxy_url(settings)
        self.assertEqual(url, "socks5h://alice:p%40ss%3Aw%2Frd@proxy.example.com:1080")
        self.assertEqual(build_proxy_url(parse_proxy_url(url)), url)

    def test_plain_socks5_scheme_is_read_as_socks5(self):
        self.assertEqual(parse_proxy_url("socks5://10.0.0.1:9050").kind, PROXY_SOCKS5)

    def test_http_without_port_or_password(self):
        settings = ProxySettings(PROXY_HTTP, "proxy.local", None, "bob")
        # The colon keeps an empty password, so Requests still authenticates.
        self.assertEqual(build_proxy_url(settings), "http://bob:@proxy.local")
        self.assertEqual(parse_proxy_url("http://bob@proxy.local").username, "bob")

    def test_ipv6_host_is_bracketed(self):
        url = build_proxy_url(ProxySettings(PROXY_HTTP, "::1", 8080))
        self.assertEqual(url, "http://[::1]:8080")
        self.assertEqual(parse_proxy_url(url).host, "::1")

    def test_no_proxy_or_missing_server_builds_empty_url(self):
        self.assertEqual(build_proxy_url(ProxySettings()), "")
        self.assertEqual(build_proxy_url(ProxySettings(PROXY_SOCKS5, "  ", 1080)), "")

    def test_https_and_socks5_schemes_are_preserved(self):
        for url in ("https://alice:pw@proxy:8443", "socks5://proxy:1080"):
            self.assertEqual(build_proxy_url(parse_proxy_url(url)), url)

    def test_credentials_keep_spaces(self):
        url = "http://%20alice%20:pw@proxy:8080"
        self.assertEqual(parse_proxy_url(url).username, " alice ")
        self.assertEqual(build_proxy_url(parse_proxy_url(url)), url)

    def test_malformed_and_unsupported_values_are_reported(self):
        self.assertEqual(parse_proxy_url("http://[::1").kind, PROXY_NONE)
        for url in ("http://[::1", "socks4://proxy:1080"):
            self.assertFalse(is_supported_proxy_url(url), url)
        self.assertTrue(is_supported_proxy_url(""))
        self.assertTrue(is_supported_proxy_url("proxy:3128"))

    def test_server_field_accepts_host_port_and_urls(self):
        self.assertEqual(split_server("proxy.local:8080"), ("proxy.local", 8080))
        self.assertEqual(split_server("http://proxy.local:3128/"), ("proxy.local", 3128))
        self.assertEqual(split_server("::1"), ("::1", None))
        self.assertEqual(split_server("[::1]:9050"), ("::1", 9050))
        self.assertEqual(split_server("bad host"), ("", None))
        url = build_proxy_url(ProxySettings(PROXY_HTTP, "proxy.local:8080"))
        self.assertEqual(url, "http://proxy.local:8080")
        url = build_proxy_url(ProxySettings(PROXY_HTTP, "proxy.local:8080", 3128))
        self.assertEqual(url, "http://proxy.local:3128")


if __name__ == "__main__":
    unittest.main()
