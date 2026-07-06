"""Centralized URL fetching with SSRF host validation and default timeouts.

All fetches of user-supplied URLs (``partition(url=...)``, ``partition_html``,
``partition_md``) route through :func:`safe_get`, which rejects requests that
resolve to non-routable addresses. The address check runs at TCP-connect time,
so the address we validate is the address we actually connect to — closing the
DNS-rebinding window that a resolve-then-connect check would leave open.

The connection/pool/adapter subclasses below reach into urllib3 internals
(``_new_conn``, ``pool_classes_by_scheme``); a urllib3 major upgrade may require
revisiting them.
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

# Ranges the ipaddress category flags don't classify but that still front
# internal infrastructure and so must be blocked.
_EXTRA_BLOCKED_NETWORKS = [
    ipaddress.ip_network("100.64.0.0/10"),  # RFC 6598 carrier-grade NAT
]

# NAT64 (RFC 6052/8215), 6to4, and IPv4-compatible IPv6 all embed an IPv4
# address; the embedded v4 is re-checked so an internal target can't be
# smuggled through a v6 wrapper.
_NAT64_NETWORKS = [
    ipaddress.ip_network("64:ff9b::/96"),
    ipaddress.ip_network("64:ff9b:1::/48"),
]
_IPV4_COMPAT_NETWORK = ipaddress.ip_network("::/96")

# Routable-looking addresses that nonetheless reach internal services.
_BLOCKED_IPS = frozenset({"168.63.129.16"})  # Azure wireserver / host agent

_DEFAULT_TIMEOUT = (10, 300)  # (connect, read) seconds
_MAX_REDIRECTS = 10
_ENV_VAR = "UNSTRUCTURED_ALLOW_PRIVATE_URL"
_TRUTHY_ENV_VALUES = frozenset({"1", "true", "yes"})

# Credential-bearing headers that must not follow a redirect to a new origin.
_REDIRECT_SENSITIVE_HEADERS = frozenset({"authorization", "cookie", "proxy-authorization"})


class UnsafeURLError(ValueError):
    """Raised when a URL targets a blocked, non-routable, or unresolvable address."""


def _env_allows_private() -> bool:
    return os.environ.get(_ENV_VAR, "").strip().lower() in _TRUTHY_ENV_VALUES


def _is_ip_blocked(ip_str: str) -> bool:
    """Return True if *ip_str* is non-routable/internal. Fail closed on parse errors."""
    if ip_str in _BLOCKED_IPS:
        return True
    try:
        addr = ipaddress.ip_address(ip_str)
    except ValueError:
        return True  # fail closed

    # Re-check the embedded IPv4 for the v6 forms that wrap one; category flags
    # on the v6 address alone don't see the inner v4.
    if isinstance(addr, ipaddress.IPv6Address):
        if addr.ipv4_mapped is not None:
            return _is_ip_blocked(str(addr.ipv4_mapped))
        if addr.sixtofour is not None:
            return _is_ip_blocked(str(addr.sixtofour))
        if any(addr in net for net in _NAT64_NETWORKS) or addr in _IPV4_COMPAT_NETWORK:
            return _is_ip_blocked(str(ipaddress.IPv4Address(int(addr) & 0xFFFFFFFF)))

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


def _validate_url(url: str, allow_private: bool = False) -> None:
    """Fast-fail scheme/host validation; the connect-time check is authoritative.

    Relying on the *resolved* address (rather than string-matching hostnames)
    also covers obfuscated literals like ``http://2130706433`` and IDN/case
    variants, since the resolver normalizes them before we classify the result.

    Skipped entirely when *allow_private* or ``UNSTRUCTURED_ALLOW_PRIVATE_URL``
    is set, for controlled fetches of internal hosts.
    """
    if allow_private or _env_allows_private():
        return

    try:
        parsed = urlparse(url)
        scheme, hostname = parsed.scheme, parsed.hostname
        _ = parsed.port  # out-of-range ports raise here rather than at connect time
    except ValueError as exc:
        raise UnsafeURLError("URL could not be parsed") from exc

    if scheme not in ("http", "https"):
        raise UnsafeURLError(f"URL scheme {scheme!r} is not allowed; use http or https")
    if not hostname:
        raise UnsafeURLError("URL is missing a hostname")

    try:
        ipaddress.ip_address(hostname)
    except ValueError:
        pass  # not a literal IP; the resolution check below handles it
    else:
        if _is_ip_blocked(hostname):
            raise UnsafeURLError("URL targets a blocked IP address")

    try:
        results = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
    except (socket.gaierror, UnicodeError, ValueError) as exc:
        raise UnsafeURLError("Failed to resolve hostname") from exc
    for *_, sockaddr in results:
        if _is_ip_blocked(sockaddr[0]):
            logger.warning("URL host %r resolves to blocked address %s", hostname, sockaddr[0])
            raise UnsafeURLError("URL hostname resolves to a blocked address")


def _safe_create_connection(
    host: str,
    port: int,
    timeout: Any,
    source_address: Optional[tuple],
    socket_options: Any,
) -> socket.socket:
    """Resolve, validate, and connect in one step so the validated IP is the IP
    we connect to (eliminates the resolve-then-connect rebinding window)."""
    if host.startswith("[") and host.endswith("]"):
        host = host[1:-1]

    infos = socket.getaddrinfo(host, port, socket.AF_UNSPEC, socket.SOCK_STREAM)

    # Reject if *any* resolved address is blocked. A split-DNS answer of
    # [public, private] must not let us connect to the public one.
    for *_, sockaddr in infos:
        if _is_ip_blocked(sockaddr[0]):
            raise UnsafeURLError(f"Hostname resolved to blocked address {sockaddr[0]}")

    last_err: Optional[Exception] = None
    for family, socktype, proto, _canonname, sockaddr in infos:
        sock = None
        try:
            sock = socket.socket(family, socktype, proto)
            if socket_options:
                for opt in socket_options:
                    sock.setsockopt(*opt)
            # _GLOBAL_DEFAULT_TIMEOUT is urllib3's "caller didn't set one" sentinel;
            # leave the socket at Python's process default in that case.
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
    """urllib3 connection that validates the resolved IP at socket-create time."""

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
    """HTTPS counterpart; only socket creation is overridden, so TLS/SNI is unchanged."""


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
    """Routes requests through :class:`_SafePoolManager`.

    Proxies are refused: a proxied connection reaches the proxy first, so the
    connection-level IP check would validate the proxy rather than the real
    target, which the proxy could then relay to any internal address.
    """

    def init_poolmanager(
        self, connections: int, maxsize: int, block: bool = False, **pool_kwargs: Any
    ) -> None:
        self.poolmanager = _SafePoolManager(
            num_pools=connections, maxsize=maxsize, block=block, **pool_kwargs
        )

    def proxy_manager_for(self, proxy: str, **proxy_kwargs: Any) -> Any:
        raise UnsafeURLError("Proxied requests are not permitted by the safe HTTP adapter")


# Stateless holder for requests' own redirect-auth logic; issues no requests.
_REDIRECT_AUTH_PROBE = requests.Session()


def _is_cross_origin(old_url: str, new_url: str) -> bool:
    """Whether credential headers must be dropped moving *old_url* → *new_url*.

    Delegates to requests' own logic so the decision tracks the library; fails
    safe (strip) on unparseable input.
    """
    try:
        return _REDIRECT_AUTH_PROBE.should_strip_auth(old_url, new_url)
    except ValueError:
        return True


def _strip_sensitive_headers(kwargs: dict) -> None:
    """Drop credential-bearing headers/kwargs before a cross-origin redirect hop."""
    headers = kwargs.get("headers")
    if headers:
        kwargs["headers"] = {
            k: v for k, v in headers.items() if k.lower() not in _REDIRECT_SENSITIVE_HEADERS
        }
    kwargs.pop("auth", None)
    kwargs.pop("cookies", None)


def safe_get(url: str, *, allow_private: bool = False, **kwargs: Any) -> requests.Response:
    """Fetch *url* with SSRF validation, a default timeout, and safe redirects.

    Redirects are followed manually (``allow_redirects`` is forced to ``False``)
    so each hop is re-validated and credential headers are dropped on
    cross-origin hops. A default ``(connect, read)`` timeout of ``(10, 300)`` is
    applied when the caller supplies none.

    Set *allow_private* (or the ``UNSTRUCTURED_ALLOW_PRIVATE_URL`` environment
    variable) to fetch internal hosts in controlled environments; that also
    permits a ``proxies=`` kwarg. All other kwargs are forwarded to
    ``requests.Session.get``.
    """
    _validate_url(url, allow_private=allow_private)
    bypass_mode = allow_private or _env_allows_private()

    if not bypass_mode and "proxies" in kwargs:
        raise UnsafeURLError("proxies kwarg is not permitted; set allow_private=True to bypass")
    if kwargs.get("timeout") is None:
        kwargs["timeout"] = _DEFAULT_TIMEOUT
    kwargs["allow_redirects"] = False

    session = requests.Session()
    if not bypass_mode:
        # Ignore HTTP(S)_PROXY / NO_PROXY / netrc: a proxy would bypass the
        # connection-level IP check.
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
            if _is_cross_origin(url, new_url):
                _strip_sensitive_headers(kwargs)
            url = new_url
        raise UnsafeURLError(f"Too many redirects (>{_MAX_REDIRECTS})")
    finally:
        session.close()
