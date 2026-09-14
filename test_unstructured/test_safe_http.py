"""Tests for centralized URL fetching with host validation."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import requests

from unstructured.safe_http import (
    UnsafeURLError,
    _is_cross_origin,
    _is_ip_blocked,
    _normalize_hostname,
    _safe_create_connection,
    _SafeHTTPAdapter,
    _strip_sensitive_headers,
    _validate_url,
    safe_get,
)

# ---------------------------------------------------------------------------
# _is_ip_blocked
# ---------------------------------------------------------------------------


class Describe_is_ip_blocked:
    """Verify that blocked and allowed IP ranges are classified correctly."""

    @pytest.mark.parametrize(
        "ip",
        [
            "127.0.0.1",
            "10.0.0.1",
            "172.16.0.1",
            "192.168.0.1",
            "169.254.169.254",
            "0.0.0.0",
            "255.255.255.255",
            "168.63.129.16",
            "224.0.0.1",
            "240.0.0.1",
            "100.64.0.1",
        ],
        ids=[
            "loopback",
            "class_a_private",
            "class_b_private",
            "class_c_private",
            "link_local",
            "this_network",
            "broadcast",
            "azure_wireserver",
            "multicast",
            "reserved_class_e",
            "cgnat",
        ],
    )
    def test_blocks_non_routable_ipv4(self, ip: str):
        assert _is_ip_blocked(ip) is True

    @pytest.mark.parametrize(
        "ip",
        ["::1", "fe80::1", "fc00::1", "fd00::1", "::"],
        ids=["loopback", "link_local", "unique_local_fc", "unique_local_fd", "unspecified"],
    )
    def test_blocks_non_routable_ipv6(self, ip: str):
        assert _is_ip_blocked(ip) is True

    def test_blocks_ipv4_mapped_ipv6(self):
        assert _is_ip_blocked("::ffff:127.0.0.1") is True
        assert _is_ip_blocked("::ffff:169.254.169.254") is True

    def test_blocks_sixtofour_embedded(self):
        # 2002:a9fe:a9fe:: wraps 169.254.169.254
        assert _is_ip_blocked("2002:a9fe:a9fe::") is True

    def test_blocks_nat64_and_ipv4_compat_embedded(self):
        assert _is_ip_blocked("64:ff9b::169.254.169.254") is True
        assert _is_ip_blocked("64:ff9b:1::169.254.169.254") is True
        assert _is_ip_blocked("::169.254.169.254") is True

    @pytest.mark.parametrize(
        "ip",
        ["8.8.8.8", "93.184.216.34", "1.1.1.1", "2607:f8b0:4004:800::200e"],
        ids=["google_dns", "example_com", "cloudflare", "google_ipv6"],
    )
    def test_allows_public_addresses(self, ip: str):
        assert _is_ip_blocked(ip) is False

    def test_fails_closed_on_unparseable_input(self):
        assert _is_ip_blocked("not-an-ip") is True
        assert _is_ip_blocked("") is True


# ---------------------------------------------------------------------------
# _normalize_hostname
# ---------------------------------------------------------------------------


class Describe_normalize_hostname:
    def test_returns_lowercase_for_ascii_input(self):
        assert _normalize_hostname("Example.COM") == "example.com"

    def test_strips_trailing_dot(self):
        assert _normalize_hostname("example.com.") == "example.com"

    def test_empty_string(self):
        assert _normalize_hostname("") == ""

    def test_idn_collapses_to_punycode(self):
        # A valid IDN encodes to its xn-- form.
        assert _normalize_hostname("Bücher.example").startswith("xn--")


# ---------------------------------------------------------------------------
# _validate_url
# ---------------------------------------------------------------------------


class Describe_validate_url:
    @pytest.mark.parametrize(
        "url",
        [
            "ftp://example.com/file",
            "file:///etc/passwd",
            "gopher://evil.com/",
            "data:text/html,<h1>hi</h1>",
            "javascript:alert(1)",
        ],
    )
    def test_rejects_non_http_scheme(self, url: str):
        with pytest.raises(UnsafeURLError, match="scheme"):
            _validate_url(url)

    def test_rejects_missing_hostname(self):
        with pytest.raises(UnsafeURLError, match="hostname"):
            _validate_url("http://")

    @pytest.mark.parametrize(
        "url",
        ["http://example.com:65536/", "http://example.com:99999/"],
        ids=["over_max", "way_over"],
    )
    def test_rejects_out_of_range_port(self, url: str):
        # Out-of-range ports must fail closed as UnsafeURLError, not leak later.
        with pytest.raises(UnsafeURLError):
            _validate_url(url)

    @pytest.mark.parametrize(
        "hostname",
        [
            "localhost",
            "metadata.google.internal",
            "metadata.gke.internal",
            "metadata.azure.com",
            "kubernetes.default",
            "kubernetes.default.svc",
            "kubernetes.default.svc.cluster.local",
        ],
    )
    def test_rejects_blocked_hostname(self, hostname: str):
        with pytest.raises(UnsafeURLError, match="blocked hostname"):
            _validate_url(f"http://{hostname}/")

    @pytest.mark.parametrize(
        "url",
        [
            "http://127.0.0.1/path",
            "http://169.254.169.254/latest/",
            "http://10.0.0.1/internal",
            "http://[::1]/path",
            "http://[::ffff:169.254.169.254]/",
        ],
        ids=["loopback", "link_local", "rfc1918", "ipv6_loopback", "ipv4_mapped"],
    )
    def test_rejects_blocked_ip_literals(self, url: str):
        with pytest.raises(UnsafeURLError, match="blocked"):
            _validate_url(url)

    @patch("unstructured.safe_http.socket.getaddrinfo")
    def test_rejects_hostname_resolving_to_non_routable(self, mock_getaddrinfo):
        mock_getaddrinfo.return_value = [(2, 1, 6, "", ("10.0.0.1", 0))]
        with pytest.raises(UnsafeURLError, match="blocked address"):
            _validate_url("http://evil.example.com/")

    @patch("unstructured.safe_http.socket.getaddrinfo")
    def test_allows_public_hostname(self, mock_getaddrinfo):
        mock_getaddrinfo.return_value = [(2, 1, 6, "", ("93.184.216.34", 0))]
        _validate_url("https://example.com/doc.pdf")  # should not raise

    @patch("unstructured.safe_http.socket.getaddrinfo")
    def test_rejects_when_any_resolved_ip_is_blocked(self, mock_getaddrinfo):
        mock_getaddrinfo.return_value = [
            (2, 1, 6, "", ("93.184.216.34", 0)),
            (2, 1, 6, "", ("10.0.0.1", 0)),
        ]
        with pytest.raises(UnsafeURLError, match="blocked address"):
            _validate_url("http://split.example.com/")

    def test_skips_validation_with_allow_private(self):
        _validate_url("http://127.0.0.1/", allow_private=True)  # should not raise

    def test_skips_validation_with_env_var(self, monkeypatch):
        monkeypatch.setenv("UNSTRUCTURED_ALLOW_PRIVATE_URL", "1")
        _validate_url("http://127.0.0.1/")  # should not raise


# ---------------------------------------------------------------------------
# _safe_create_connection
# ---------------------------------------------------------------------------


class Describe_safe_create_connection:
    @patch("unstructured.safe_http.socket.getaddrinfo")
    def test_rejects_blocked_resolved_address_at_connect(self, mock_getaddrinfo):
        mock_getaddrinfo.return_value = [(2, 1, 6, "", ("10.0.0.1", 0))]
        with pytest.raises(UnsafeURLError, match="blocked address"):
            _safe_create_connection("evil.example.com", 80, None, None, None)

    @patch("unstructured.safe_http.socket.socket")
    @patch("unstructured.safe_http.socket.getaddrinfo")
    def test_connects_to_validated_public_address(self, mock_getaddrinfo, MockSocket):
        mock_getaddrinfo.return_value = [(2, 1, 6, "", ("93.184.216.34", 80))]
        sock = MockSocket.return_value
        result = _safe_create_connection("example.com", 80, None, None, None)
        assert result is sock
        sock.connect.assert_called_once_with(("93.184.216.34", 80))

    @patch("unstructured.safe_http.socket.getaddrinfo")
    def test_strips_ipv6_brackets(self, mock_getaddrinfo):
        mock_getaddrinfo.return_value = [(10, 1, 6, "", ("::1", 80, 0, 0))]
        with pytest.raises(UnsafeURLError):
            _safe_create_connection("[::1]", 80, None, None, None)


# ---------------------------------------------------------------------------
# safe_get
# ---------------------------------------------------------------------------


class Describe_safe_get:
    @patch("unstructured.safe_http.socket.getaddrinfo")
    @patch("unstructured.safe_http.requests.Session")
    def test_returns_response_for_public_url(self, MockSession, mock_getaddrinfo):
        mock_getaddrinfo.return_value = [(2, 1, 6, "", ("93.184.216.34", 0))]
        mock_response = MagicMock(spec=requests.Response)
        mock_response.is_redirect = False
        session_instance = MockSession.return_value
        session_instance.get.return_value = mock_response

        result = safe_get("https://example.com/doc.pdf")

        assert result is mock_response
        session_instance.get.assert_called_once()
        session_instance.close.assert_called_once()

    @patch("unstructured.safe_http.socket.getaddrinfo")
    @patch("unstructured.safe_http.requests.Session")
    def test_applies_default_timeout(self, MockSession, mock_getaddrinfo):
        mock_getaddrinfo.return_value = [(2, 1, 6, "", ("93.184.216.34", 0))]
        mock_response = MagicMock(spec=requests.Response)
        mock_response.is_redirect = False
        MockSession.return_value.get.return_value = mock_response

        safe_get("https://example.com/doc.pdf")

        assert MockSession.return_value.get.call_args[1]["timeout"] == (10, 300)

    @patch("unstructured.safe_http.socket.getaddrinfo")
    @patch("unstructured.safe_http.requests.Session")
    def test_respects_explicit_timeout(self, MockSession, mock_getaddrinfo):
        mock_getaddrinfo.return_value = [(2, 1, 6, "", ("93.184.216.34", 0))]
        mock_response = MagicMock(spec=requests.Response)
        mock_response.is_redirect = False
        MockSession.return_value.get.return_value = mock_response

        safe_get("https://example.com/doc.pdf", timeout=5)

        assert MockSession.return_value.get.call_args[1]["timeout"] == 5

    @patch("unstructured.safe_http.socket.getaddrinfo")
    @patch("unstructured.safe_http.requests.Session")
    def test_forces_allow_redirects_false(self, MockSession, mock_getaddrinfo):
        mock_getaddrinfo.return_value = [(2, 1, 6, "", ("93.184.216.34", 0))]
        mock_response = MagicMock(spec=requests.Response)
        mock_response.is_redirect = False
        MockSession.return_value.get.return_value = mock_response

        safe_get("https://example.com/doc.pdf", allow_redirects=True)

        assert MockSession.return_value.get.call_args[1]["allow_redirects"] is False

    @patch("unstructured.safe_http.socket.getaddrinfo")
    @patch("unstructured.safe_http.requests.Session")
    def test_validates_redirect_targets(self, MockSession, mock_getaddrinfo):
        mock_getaddrinfo.side_effect = [
            [(2, 1, 6, "", ("93.184.216.34", 0))],  # initial URL
            [(2, 1, 6, "", ("10.0.0.1", 0))],  # redirect target
        ]
        redirect_response = MagicMock(spec=requests.Response)
        redirect_response.is_redirect = True
        redirect_response.headers = {"Location": "http://internal.corp/secret"}
        redirect_response.url = "https://example.com/doc.pdf"
        MockSession.return_value.get.return_value = redirect_response

        with pytest.raises(UnsafeURLError, match="blocked address"):
            safe_get("https://example.com/doc.pdf")

    @patch("unstructured.safe_http.socket.getaddrinfo")
    @patch("unstructured.safe_http.requests.Session")
    def test_follows_valid_redirect_chain(self, MockSession, mock_getaddrinfo):
        mock_getaddrinfo.return_value = [(2, 1, 6, "", ("93.184.216.34", 0))]
        redirect_response = MagicMock(spec=requests.Response)
        redirect_response.is_redirect = True
        redirect_response.headers = {"Location": "https://cdn.example.com/doc.pdf"}
        redirect_response.url = "https://example.com/doc.pdf"
        final_response = MagicMock(spec=requests.Response)
        final_response.is_redirect = False
        MockSession.return_value.get.side_effect = [redirect_response, final_response]

        result = safe_get("https://example.com/doc.pdf")

        assert result is final_response
        assert MockSession.return_value.get.call_count == 2

    @patch("unstructured.safe_http.socket.getaddrinfo")
    @patch("unstructured.safe_http.requests.Session")
    def test_enforces_max_redirects(self, MockSession, mock_getaddrinfo):
        mock_getaddrinfo.return_value = [(2, 1, 6, "", ("93.184.216.34", 0))]
        redirect_response = MagicMock(spec=requests.Response)
        redirect_response.is_redirect = True
        redirect_response.headers = {"Location": "https://example.com/again"}
        redirect_response.url = "https://example.com/doc.pdf"
        MockSession.return_value.get.return_value = redirect_response

        with pytest.raises(UnsafeURLError, match="Too many redirects"):
            safe_get("https://example.com/doc.pdf")

    @patch("unstructured.safe_http.socket.getaddrinfo")
    @patch("unstructured.safe_http.requests.Session")
    def test_returns_response_on_missing_location_header(self, MockSession, mock_getaddrinfo):
        mock_getaddrinfo.return_value = [(2, 1, 6, "", ("93.184.216.34", 0))]
        redirect_response = MagicMock(spec=requests.Response)
        redirect_response.is_redirect = True
        redirect_response.headers = {}
        redirect_response.url = "https://example.com/doc.pdf"
        MockSession.return_value.get.return_value = redirect_response

        result = safe_get("https://example.com/doc.pdf")
        assert result is redirect_response

    def test_rejects_non_routable_url_without_fetch(self):
        with pytest.raises(UnsafeURLError):
            safe_get("http://169.254.169.254/latest/meta-data/")

    @patch("unstructured.safe_http.socket.getaddrinfo")
    @patch("unstructured.safe_http.requests.Session")
    def test_session_closed_on_validation_error(self, MockSession, mock_getaddrinfo):
        mock_getaddrinfo.side_effect = [
            [(2, 1, 6, "", ("93.184.216.34", 0))],
            [(2, 1, 6, "", ("10.0.0.1", 0))],
        ]
        redirect_response = MagicMock(spec=requests.Response)
        redirect_response.is_redirect = True
        redirect_response.headers = {"Location": "http://internal.corp/"}
        redirect_response.url = "https://example.com/doc.pdf"
        MockSession.return_value.get.return_value = redirect_response

        with pytest.raises(UnsafeURLError):
            safe_get("https://example.com/doc.pdf")
        MockSession.return_value.close.assert_called_once()

    @patch("unstructured.safe_http.socket.getaddrinfo")
    def test_rejects_proxies_kwarg(self, mock_getaddrinfo):
        mock_getaddrinfo.return_value = [(2, 1, 6, "", ("93.184.216.34", 0))]
        with pytest.raises(UnsafeURLError, match="proxies"):
            safe_get("https://example.com/doc.pdf", proxies={"https": "http://proxy:8080"})


# ---------------------------------------------------------------------------
# safe_get adapter mounting / opt-out
# ---------------------------------------------------------------------------


class Describe_safe_get_mounts_adapter:
    @patch("unstructured.safe_http.socket.getaddrinfo")
    @patch("unstructured.safe_http.requests.Session")
    def test_mounts_safe_adapter_and_disables_trust_env(self, MockSession, mock_getaddrinfo):
        mock_getaddrinfo.return_value = [(2, 1, 6, "", ("93.184.216.34", 0))]
        mock_response = MagicMock(spec=requests.Response)
        mock_response.is_redirect = False
        session_instance = MockSession.return_value
        session_instance.get.return_value = mock_response

        safe_get("https://example.com/doc.pdf")

        assert session_instance.trust_env is False
        mounted = [c.args[1] for c in session_instance.mount.call_args_list]
        assert all(isinstance(a, _SafeHTTPAdapter) for a in mounted)

    @patch("unstructured.safe_http.requests.Session")
    def test_allow_private_skips_adapter_and_permits_proxies(self, MockSession):
        mock_response = MagicMock(spec=requests.Response)
        mock_response.is_redirect = False
        session_instance = MockSession.return_value
        session_instance.get.return_value = mock_response

        # No getaddrinfo patch: allow_private must skip resolution entirely.
        result = safe_get(
            "http://127.0.0.1/internal",
            allow_private=True,
            proxies={"http": "http://proxy:8080"},
        )
        assert result is mock_response
        session_instance.mount.assert_not_called()


class Describe_SafeHTTPAdapter:
    def test_proxy_manager_is_refused(self):
        adapter = _SafeHTTPAdapter()
        with pytest.raises(UnsafeURLError, match="Proxied requests"):
            adapter.proxy_manager_for("http://proxy:8080")


# ---------------------------------------------------------------------------
# _is_cross_origin / _strip_sensitive_headers (redirect credential handling)
# ---------------------------------------------------------------------------


class Describe_is_cross_origin:
    def test_same_origin_not_cross(self):
        assert _is_cross_origin("https://example.com/a", "https://example.com/b") is False

    def test_different_host_is_cross(self):
        assert _is_cross_origin("https://a.com/", "https://b.com/") is True

    def test_http_to_https_upgrade_is_not_cross(self):
        assert _is_cross_origin("http://example.com/", "https://example.com/") is False

    def test_downgrade_on_same_nondefault_port_is_cross(self):
        assert _is_cross_origin("https://host:9000/a", "http://host:9000/b") is True

    def test_explicit_default_port_same_origin_not_cross(self):
        assert _is_cross_origin("https://example.com:443/a", "https://example.com/b") is False

    def test_unparseable_port_fails_safe(self):
        assert _is_cross_origin("http://a.com:abc/", "http://a.com/") is True


class Describe_strip_sensitive_headers:
    def test_removes_credential_headers(self):
        kwargs = {
            "headers": {
                "Authorization": "Bearer x",
                "Cookie": "s=y",
                "Proxy-Authorization": "Basic z",
                "User-Agent": "tests",
            }
        }
        _strip_sensitive_headers(kwargs)
        assert kwargs["headers"] == {"User-Agent": "tests"}

    def test_removes_auth_and_cookies_kwargs(self):
        kwargs = {"auth": ("u", "p"), "cookies": {"s": "y"}, "timeout": 5}
        _strip_sensitive_headers(kwargs)
        assert "auth" not in kwargs
        assert "cookies" not in kwargs
        assert kwargs["timeout"] == 5

    def test_no_headers_is_noop(self):
        kwargs: dict = {}
        _strip_sensitive_headers(kwargs)
        assert kwargs == {}


class Describe_safe_get_redirect_auth_strip:
    @patch("unstructured.safe_http.socket.getaddrinfo")
    @patch("unstructured.safe_http.requests.Session")
    def test_strips_credentials_on_cross_origin_redirect(self, MockSession, mock_getaddrinfo):
        mock_getaddrinfo.return_value = [(2, 1, 6, "", ("93.184.216.34", 0))]
        redirect_response = MagicMock(spec=requests.Response)
        redirect_response.is_redirect = True
        redirect_response.headers = {"Location": "https://evil.com/x"}
        redirect_response.url = "https://trusted.com/doc"
        final_response = MagicMock(spec=requests.Response)
        final_response.is_redirect = False
        session_instance = MockSession.return_value
        session_instance.get.side_effect = [redirect_response, final_response]

        safe_get("https://trusted.com/doc", headers={"Authorization": "Bearer secret"})

        second_call_headers = session_instance.get.call_args_list[1][1].get("headers", {})
        assert "Authorization" not in second_call_headers
