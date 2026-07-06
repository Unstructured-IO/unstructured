"""Tests for `unstructured.safe_http` SSRF validation."""

from __future__ import annotations

import contextlib
import socket
from unittest.mock import patch

import pytest

from unstructured.safe_http import (
    UnsafeURLError,
    _is_cross_origin,
    _is_ip_blocked,
    _safe_create_connection,
    _SafeHTTPAdapter,
    _strip_sensitive_headers,
    _validate_url,
    safe_get,
)


def _addrinfo(*ips: str):
    """Build getaddrinfo-shaped results for the given IPs."""
    return [
        (socket.AF_INET6 if ":" in ip else socket.AF_INET, socket.SOCK_STREAM, 0, "", (ip, 0))
        for ip in ips
    ]


def _getaddrinfo_for(mapping: dict[str, list[str]]):
    def _fake(host: str, *_args, **_kwargs):
        if host not in mapping:
            raise socket.gaierror(f"unknown host {host!r}")
        return _addrinfo(*mapping[host])

    return _fake


# ---------------------------------------------------------------------------
# _is_ip_blocked
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "ip",
    [
        "127.0.0.1",
        "127.255.255.255",
        "10.0.0.1",
        "172.16.0.1",
        "192.168.1.1",
        "169.254.169.254",  # link-local — cloud metadata
        "100.64.0.1",  # CGNAT
        "168.63.129.16",  # Azure wireserver
        "0.0.0.0",
        "255.255.255.255",
        "::1",
        "fe80::1",
        "fc00::1",
        "fd00::1",
        "::",
        "::ffff:127.0.0.1",  # IPv4-mapped loopback
        "::ffff:169.254.169.254",  # IPv4-mapped metadata
        "64:ff9b::169.254.169.254",  # NAT64-embedded metadata
        "not-an-ip",  # fail closed
    ],
)
def test_is_ip_blocked_blocks_internal_and_unparseable(ip: str):
    assert _is_ip_blocked(ip) is True


@pytest.mark.parametrize("ip", ["8.8.8.8", "93.184.216.34", "1.1.1.1", "2606:4700:4700::1111"])
def test_is_ip_blocked_allows_public(ip: str):
    assert _is_ip_blocked(ip) is False


# ---------------------------------------------------------------------------
# _validate_url
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "url", ["ftp://example.com", "file:///etc/passwd", "gopher://x/", "data:,x"]
)
def test_validate_url_rejects_non_http_scheme(url: str):
    with pytest.raises(UnsafeURLError):
        _validate_url(url)


def test_validate_url_rejects_missing_hostname():
    with pytest.raises(UnsafeURLError):
        _validate_url("http:///path")


@pytest.mark.parametrize(
    "url", ["http://127.0.0.1/admin", "https://169.254.169.254/latest/meta-data", "http://[::1]/"]
)
def test_validate_url_rejects_literal_blocked_ip(url: str):
    with pytest.raises(UnsafeURLError):
        _validate_url(url)


def test_validate_url_rejects_host_resolving_to_blocked():
    with patch(
        "unstructured.safe_http.socket.getaddrinfo", _getaddrinfo_for({"evil.test": ["10.0.0.5"]})
    ):
        with pytest.raises(UnsafeURLError):
            _validate_url("http://evil.test/")


def test_validate_url_rejects_split_dns_with_any_blocked():
    with patch(
        "unstructured.safe_http.socket.getaddrinfo",
        _getaddrinfo_for({"rebind.test": ["93.184.216.34", "10.0.0.5"]}),
    ):
        with pytest.raises(UnsafeURLError):
            _validate_url("http://rebind.test/")


def test_validate_url_allows_host_resolving_to_public():
    with patch(
        "unstructured.safe_http.socket.getaddrinfo",
        _getaddrinfo_for({"good.test": ["93.184.216.34"]}),
    ):
        _validate_url("http://good.test/")  # no raise


def test_validate_url_fails_closed_on_resolution_error():
    with patch("unstructured.safe_http.socket.getaddrinfo", side_effect=socket.gaierror):
        with pytest.raises(UnsafeURLError):
            _validate_url("http://nxdomain.test/")


def test_validate_url_skipped_by_allow_private():
    _validate_url("http://127.0.0.1/", allow_private=True)  # no raise


def test_validate_url_skipped_by_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("UNSTRUCTURED_ALLOW_PRIVATE_URL", "1")
    _validate_url("http://127.0.0.1/")  # no raise


# ---------------------------------------------------------------------------
# cross-origin credential handling
# ---------------------------------------------------------------------------


def test_is_cross_origin_true_for_different_host():
    assert _is_cross_origin("https://a.test/x", "https://b.test/y") is True


def test_is_cross_origin_false_for_same_host():
    assert _is_cross_origin("https://a.test/x", "https://a.test/y") is False


def test_strip_sensitive_headers_removes_credentials():
    kwargs = {
        "headers": {"Authorization": "secret", "Cookie": "s=1", "User-Agent": "ua"},
        "auth": ("u", "p"),
        "cookies": {"c": "1"},
    }
    _strip_sensitive_headers(kwargs)
    assert kwargs["headers"] == {"User-Agent": "ua"}
    assert "auth" not in kwargs
    assert "cookies" not in kwargs


# ---------------------------------------------------------------------------
# safe_get
# ---------------------------------------------------------------------------


class _FakeResp:
    def __init__(self, status_code: int = 200, headers=None, url: str = "https://example.test/"):
        self.status_code = status_code
        self.headers = headers or {}
        self.url = url

    @property
    def is_redirect(self) -> bool:
        return self.status_code in (301, 302, 303, 307, 308) and "Location" in self.headers


class _FakeSession:
    def __init__(self, responses):
        self._responses = list(responses)
        self.get_calls: list[tuple] = []
        self.trust_env = True
        self.mounts: dict = {}

    def mount(self, prefix, adapter):
        self.mounts[prefix] = adapter

    def get(self, url, **kwargs):
        self.get_calls.append((url, kwargs))
        return self._responses.pop(0)

    def close(self):
        pass


@contextlib.contextmanager
def _fake_http(responses, resolves: str = "93.184.216.34"):
    """Patch the outbound Session and DNS resolution used by `safe_get`."""
    fake = _FakeSession(responses)
    with (
        patch("unstructured.safe_http.requests.Session", return_value=fake),
        patch("unstructured.safe_http.socket.getaddrinfo", lambda *a, **k: _addrinfo(resolves)),
    ):
        yield fake


def test_safe_get_applies_default_timeout_and_disables_redirects():
    with _fake_http([_FakeResp(200)]) as fake:
        resp = safe_get("https://example.test/doc")

    assert resp.status_code == 200
    _url, kwargs = fake.get_calls[0]
    assert kwargs["timeout"] == (10, 300)
    assert kwargs["allow_redirects"] is False
    assert fake.trust_env is False


def test_safe_get_preserves_caller_timeout():
    with _fake_http([_FakeResp(200)]) as fake:
        safe_get("https://example.test/doc", timeout=5)
    assert fake.get_calls[0][1]["timeout"] == 5


def test_safe_get_refuses_proxies_in_secure_mode():
    with _fake_http([_FakeResp(200)]):
        with pytest.raises(UnsafeURLError):
            safe_get("https://example.test/", proxies={"http": "http://p"})


def test_safe_get_rejects_redirect_to_blocked_target():
    responses = [_FakeResp(302, {"Location": "http://169.254.169.254/imds"})]
    with _fake_http(responses):
        with pytest.raises(UnsafeURLError):
            safe_get("https://example.test/start")


def test_safe_get_strips_credentials_on_cross_origin_redirect():
    responses = [
        _FakeResp(302, {"Location": "https://evil.test/"}, url="https://example.test/"),
        _FakeResp(200, url="https://evil.test/"),
    ]
    with _fake_http(responses) as fake:
        safe_get("https://example.test/start", headers={"Authorization": "secret", "X-Keep": "1"})

    assert fake.get_calls[0][1]["headers"].get("Authorization") == "secret"
    assert "Authorization" not in fake.get_calls[1][1]["headers"]
    assert fake.get_calls[1][1]["headers"].get("X-Keep") == "1"


def test_safe_get_keeps_credentials_on_same_origin_redirect():
    responses = [
        _FakeResp(302, {"Location": "https://example.test/next"}, url="https://example.test/"),
        _FakeResp(200, url="https://example.test/next"),
    ]
    with _fake_http(responses) as fake:
        safe_get("https://example.test/start", headers={"Authorization": "secret"})
    assert fake.get_calls[1][1]["headers"].get("Authorization") == "secret"


def test_safe_get_raises_on_too_many_redirects():
    responses = [
        _FakeResp(302, {"Location": "https://example.test/loop"}, url="https://example.test/")
        for _ in range(10)
    ]
    with _fake_http(responses):
        with pytest.raises(UnsafeURLError, match="Too many redirects"):
            safe_get("https://example.test/start")


def test_safe_get_allow_private_bypasses_validation_and_adapter():
    with _fake_http([_FakeResp(200)]) as fake:
        resp = safe_get("http://127.0.0.1/admin", allow_private=True)

    assert resp.status_code == 200
    assert fake.trust_env is True  # bypass mode leaves proxy/env handling intact
    assert fake.mounts == {}  # no safe adapter mounted


# ---------------------------------------------------------------------------
# connect-time validation + adapter
# ---------------------------------------------------------------------------


def test_safe_create_connection_rejects_blocked_resolved_address():
    with patch("unstructured.safe_http.socket.getaddrinfo", lambda *a, **k: _addrinfo("10.0.0.9")):
        with pytest.raises(UnsafeURLError):
            _safe_create_connection("internal.test", 80, None, None, None)


def test_safe_adapter_refuses_proxies():
    adapter = _SafeHTTPAdapter()
    with pytest.raises(UnsafeURLError):
        adapter.proxy_manager_for("http://proxy.test:8080")
