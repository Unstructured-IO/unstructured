"""Centralized URL fetching with host validation and default timeouts.

All HTTP fetches of user-supplied URLs should go through :func:`safe_get` so
that scheme, hostname, and IP-range checks are applied consistently.
"""

from __future__ import annotations

import ipaddress
import logging
import os
import socket
from typing import Any, Optional
from urllib.parse import urljoin, urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.connection import HTTPConnection, HTTPSConnection
from urllib3.connectionpool import HTTPConnectionPool, HTTPSConnectionPool
from urllib3.exceptions import NameResolutionError
from urllib3.poolmanager import PoolManager

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Blocked network ranges
# ---------------------------------------------------------------------------

# Ranges that ipaddress category flags don't classify but must still be blocked.
_EXTRA_BLOCKED_NETWORKS = [
    ipaddress.ip_network("100.64.0.0/10"),  # RFC 6598 CGNAT
]

# NAT64 (RFC 6052/8215) and IPv4-compatible IPv6 embed an IPv4 in the low 32 bits.
_NAT64_NETWORKS = [
    ipaddress.ip_network("64:ff9b::/96"),
    ipaddress.ip_network("64:ff9b:1::/48"),
]
_IPV4_COMPAT_NETWORK = ipaddress.ip_network("::/96")

_BLOCKED_HOSTNAMES = frozenset(
    [
        "localhost",
        "metadata.google.internal",
        "metadata.gke.internal",
        "metadata.azure.com",
        "kubernetes.default",
        "kubernetes.default.svc",
        "kubernetes.default.svc.cluster.local",
    ]
)

_BLOCKED_IPS = frozenset(
    [
        "255.255.255.255",
        "168.63.129.16",  # Azure wireserver
    ]
)

_DEFAULT_TIMEOUT = (10, 300)  # (connect, read) seconds
_MAX_REDIRECTS = 10
_ENV_VAR = "UNSTRUCTURED_ALLOW_PRIVATE_URL"
_TRUTHY_ENV_VALUES = frozenset({"1", "true", "yes"})


def _env_allows_private() -> bool:
    """Return True when the escape-hatch env var is set to a truthy value."""
    return os.environ.get(_ENV_VAR, "").strip().lower() in _TRUTHY_ENV_VALUES


class UnsafeURLError(ValueError):
    """Raised when a URL targets a blocked or non-routable address."""


# ---------------------------------------------------------------------------
# IP / hostname helpers
# ---------------------------------------------------------------------------


def _is_ip_blocked(ip_str: str) -> bool:
    """Return True if *ip_str* is non-routable/internal. Fail-closed on parse errors."""
    if ip_str in _BLOCKED_IPS:
        return True

    try:
        addr = ipaddress.ip_address(ip_str)
    except ValueError:
        return True  # fail closed

    # Unwrap IPv6 forms that embed an IPv4 address, then re-check the inner v4.
    if isinstance(addr, ipaddress.IPv6Address):
        if addr.ipv4_mapped is not None:  # ::ffff:0:0/96
            return _is_ip_blocked(str(addr.ipv4_mapped))
        if addr.sixtofour is not None:  # 2002::/16
            return _is_ip_blocked(str(addr.sixtofour))
        if any(addr in net for net in _NAT64_NETWORKS) or addr in _IPV4_COMPAT_NETWORK:
            return _is_ip_blocked(str(ipaddress.IPv4Address(int(addr) & 0xFFFFFFFF)))

    # Category flags cover loopback/private/link-local/reserved/multicast/
    # unspecified for both v4 and v6; _EXTRA_BLOCKED_NETWORKS adds ranges the
    # stdlib doesn't classify (CGNAT).
    if (
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_reserved
        or addr.is_multicast
        or addr.is_unspecified
    ):
        return True
    return any(addr in net for net in _EXTRA_BLOCKED_NETWORKS)


def _normalize_hostname(hostname: str) -> str:
    """Lowercase, strip trailing dots, and IDNA-encode for denylist comparison.

    Falls back to the lowercased form when IDNA encoding can't proceed; the
    subsequent DNS resolution step then catches outright-invalid names.
    """
    base = hostname.lower().rstrip(".")
    if not base:
        return base
    try:
        return base.encode("idna").decode("ascii").lower().rstrip(".")
    except UnicodeError:
        return base


# ---------------------------------------------------------------------------
# Pre-request URL validation (fast-fail UX layer)
# ---------------------------------------------------------------------------


def _validate_url(url: str, allow_private: bool = False) -> None:
    """Pre-request validation. Connect-time check in _SafeHTTPConnection is authoritative.

    Skipped entirely when ``allow_private`` is True or the
    ``UNSTRUCTURED_ALLOW_PRIVATE_URL`` env var is truthy.
    """
    if allow_private or _env_allows_private():
        return

    try:
        parsed = urlparse(url)
        _ = parsed.port  # out-of-range ports raise ValueError here, not later
    except ValueError as exc:
        raise UnsafeURLError("URL could not be parsed") from exc

    if parsed.scheme not in ("http", "https"):
        raise UnsafeURLError(
            f"URL scheme {parsed.scheme!r} is not allowed; only http and https are accepted"
        )

    hostname = parsed.hostname
    if not hostname:
        raise UnsafeURLError("URL is missing a hostname")

    normalized = _normalize_hostname(hostname)
    if normalized in _BLOCKED_HOSTNAMES:
        raise UnsafeURLError("URL targets a blocked hostname")

    # Catch literal IPs (decimal/hex/octal variants ipaddress can parse) up front.
    try:
        ipaddress.ip_address(hostname)
    except ValueError:
        pass
    else:
        if _is_ip_blocked(hostname):
            raise UnsafeURLError("URL targets a blocked IP address")

    # Fast-fail DNS check.  Authoritative check happens at connect time in
    # _SafeHTTPConnection — this one just avoids a wasted TCP handshake.
    try:
        results = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
    except (socket.gaierror, UnicodeError, ValueError) as exc:
        raise UnsafeURLError("Failed to resolve hostname") from exc

    for _family, _socktype, _proto, _canonname, sockaddr in results:
        ip = sockaddr[0]
        if _is_ip_blocked(ip):
            logger.warning("URL hostname %r resolves to blocked address %s", hostname, ip)
            raise UnsafeURLError("URL hostname resolves to a blocked address")


# ---------------------------------------------------------------------------
# Connect-time validation
# ---------------------------------------------------------------------------


def _safe_create_connection(
    host: str,
    port: int,
    timeout: Any,
    source_address: Optional[tuple],
    socket_options: Any,
) -> socket.socket:
    """Resolve, validate, and connect — all in one atomic step.

    The resolved IP we validate is the IP we connect to, eliminating the
    DNS-rebinding window between pre-request resolution and TCP connect.
    """
    if host.startswith("[") and host.endswith("]"):
        host = host[1:-1]

    try:
        infos = socket.getaddrinfo(host, port, socket.AF_UNSPEC, socket.SOCK_STREAM)
    except socket.gaierror:
        raise

    # Reject if *any* resolved address is blocked. A split-DNS response of
    # [public, private] should not let us connect to the public one — the
    # presence of the private one is a strong signal of a rebinding probe.
    for _family, _socktype, _proto, _canonname, sockaddr in infos:
        ip = sockaddr[0]
        if _is_ip_blocked(ip):
            raise UnsafeURLError(f"Hostname resolved to blocked address {ip} at connect time")

    last_err: Optional[Exception] = None
    for family, socktype, proto, _canonname, sockaddr in infos:
        sock = None
        try:
            sock = socket.socket(family, socktype, proto)
            if socket_options:
                for opt in socket_options:
                    sock.setsockopt(*opt)
            # socket._GLOBAL_DEFAULT_TIMEOUT is the sentinel urllib3 passes when
            # the caller didn't specify one; don't call settimeout in that case
            # so the socket inherits Python's process-wide default.
            if timeout is not None and timeout is not socket._GLOBAL_DEFAULT_TIMEOUT:
                sock.settimeout(timeout)
            if source_address:
                sock.bind(source_address)
            sock.connect(sockaddr)
            return sock
        except OSError as e:
            last_err = e
            if sock is not None:
                sock.close()

    if last_err is not None:
        raise last_err
    raise OSError(f"getaddrinfo returned no usable addresses for {host!r}")


class _SafeHTTPConnection(HTTPConnection):
    """urllib3 ``HTTPConnection`` that validates the resolved IP at socket-create time."""

    def _new_conn(self) -> socket.socket:
        try:
            return _safe_create_connection(
                self._dns_host,
                self.port,
                self.timeout,
                self.source_address,
                self.socket_options,
            )
        except UnsafeURLError:
            raise
        except socket.gaierror as e:
            raise NameResolutionError(self.host, self, e) from e


class _SafeHTTPSConnection(_SafeHTTPConnection, HTTPSConnection):
    """HTTPS counterpart — inherits ``_new_conn`` from :class:`_SafeHTTPConnection`.

    TLS handshake / SNI handling is unchanged (we override only the socket
    creation step, not the wrapping that follows).
    """


class _SafeHTTPConnectionPool(HTTPConnectionPool):
    ConnectionCls = _SafeHTTPConnection


class _SafeHTTPSConnectionPool(HTTPSConnectionPool):
    ConnectionCls = _SafeHTTPSConnection


class _SafePoolManager(PoolManager):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.pool_classes_by_scheme = {
            "http": _SafeHTTPConnectionPool,
            "https": _SafeHTTPSConnectionPool,
        }


class _SafeHTTPAdapter(HTTPAdapter):
    """``requests`` adapter that routes through :class:`_SafePoolManager`.

    Proxy paths are refused: a proxied connection reaches the proxy host
    first, so the connection-level IP check would validate the proxy
    rather than the real target, and the proxy could then relay to any
    internal address.  Callers needing proxy support must opt out of
    validation via ``allow_private=True``.
    """

    def init_poolmanager(
        self,
        connections: int,
        maxsize: int,
        block: bool = False,
        **pool_kwargs: Any,
    ) -> None:
        self.poolmanager = _SafePoolManager(
            num_pools=connections, maxsize=maxsize, block=block, **pool_kwargs
        )

    def proxy_manager_for(self, proxy: str, **proxy_kwargs: Any) -> Any:
        raise UnsafeURLError("Proxied requests are not permitted through the safe HTTP adapter")


# ---------------------------------------------------------------------------
# Cross-origin redirect handling
# ---------------------------------------------------------------------------


# Credential-bearing headers that must not carry to a new origin on redirect.
_REDIRECT_SENSITIVE_HEADERS = frozenset({"authorization", "cookie", "proxy-authorization"})

# Stateless holder for requests' own redirect-auth logic; issues no requests.
_REDIRECT_AUTH_PROBE = requests.Session()


def _is_cross_origin(old_url: str, new_url: str) -> bool:
    """Return True when credential material must not carry from *old_url* to *new_url*.

    Delegates to :meth:`requests.Session.should_strip_auth`; fails safe (strip)
    on unparseable input.
    """
    try:
        return _REDIRECT_AUTH_PROBE.should_strip_auth(old_url, new_url)
    except ValueError:
        return True


def _strip_sensitive_headers(kwargs: dict) -> None:
    """Drop credential headers and the ``auth``/``cookies`` kwargs before a cross-origin hop."""
    headers = kwargs.get("headers")
    if headers:
        kwargs["headers"] = {
            k: v for k, v in headers.items() if k.lower() not in _REDIRECT_SENSITIVE_HEADERS
        }
    kwargs.pop("auth", None)
    kwargs.pop("cookies", None)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def safe_get(
    url: str,
    *,
    allow_private: bool = False,
    **kwargs: Any,
) -> requests.Response:
    """Fetch *url* with pre-request validation and connect-time IP validation.

    Redirects are followed manually (``allow_redirects`` is always forced to
    ``False``); each hop is re-validated. A default timeout of ``(10, 300)``
    (connect, read) is applied when none is provided.

    Parameters
    ----------
    url:
        Target URL.
    allow_private:
        When True, URL validation and connect-time IP validation are
        skipped, and ``proxies=`` may be supplied. Also settable via the
        ``UNSTRUCTURED_ALLOW_PRIVATE_URL`` environment variable.
    **kwargs:
        Forwarded to ``requests.Session.get``.
    """
    _validate_url(url, allow_private=allow_private)

    bypass_mode = allow_private or _env_allows_private()
    if not bypass_mode and "proxies" in kwargs:
        # Proxies route through a third-party host that we can't apply the
        # connection-level IP check to; refuse rather than silently weakening
        # the guarantee.
        raise UnsafeURLError("proxies kwarg is not permitted; set allow_private=True to bypass")

    if kwargs.get("timeout") is None:
        kwargs["timeout"] = _DEFAULT_TIMEOUT
    kwargs["allow_redirects"] = False

    session = requests.Session()
    if not bypass_mode:
        # Disable auto-pickup of HTTP_PROXY / HTTPS_PROXY / NO_PROXY env vars,
        # plus netrc and CA bundle env-var overrides.
        session.trust_env = False
        adapter = _SafeHTTPAdapter()
        session.mount("http://", adapter)
        session.mount("https://", adapter)

    try:
        for _ in range(_MAX_REDIRECTS):
            response = session.get(url, **kwargs)
            if not response.is_redirect:
                return response

            location = response.headers.get("Location")
            if not location:
                return response  # malformed redirect — return as-is

            new_url = urljoin(response.url, location)
            _validate_url(new_url, allow_private=allow_private)
            # Drop credential material on cross-origin hops (matches requests).
            if _is_cross_origin(url, new_url):
                _strip_sensitive_headers(kwargs)
            url = new_url
        raise UnsafeURLError(f"Too many redirects (>{_MAX_REDIRECTS})")
    finally:
        session.close()
