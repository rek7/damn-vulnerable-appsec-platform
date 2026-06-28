"""SSRF guard for git URLs and the always-on link-local/metadata block (§13).

Two independent controls live here:

1. ``validate_git_url`` — gate ``source_type=git`` clones. The worker re-validates
   even though the API already validated, because the worker is the thing that
   actually opens the socket.
2. ``is_blocked_beacon_host`` — ensure worker-emitted beacons can only target
   the bundled in-network listener hostname.
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

from . import config


class SSRFError(ValueError):
    """Raised when a git URL fails the SSRF guard."""


def _ip_is_disallowed(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """True if an IP is private/loopback/link-local/reserved/metadata."""
    if str(ip) in config.METADATA_IPS:
        return True
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def _resolve_addresses(host: str) -> list[str]:
    """Resolve a hostname to all of its A/AAAA addresses (may raise)."""
    infos = socket.getaddrinfo(host, None)
    return list({str(info[4][0]) for info in infos})


def validate_git_url(url: str, *, resolve: bool = True) -> str:
    """Validate a git clone URL against the SSRF allowlist (§13).

    Returns the normalized URL on success; raises SSRFError otherwise. When
    ``resolve`` is False, DNS resolution is skipped (useful in tests that should
    not hit the network) but every non-network rule is still enforced.
    """
    parsed = urlparse(url)

    if parsed.scheme != "https":
        raise SSRFError(f"scheme must be https, got {parsed.scheme!r}")

    if "@" in parsed.netloc or parsed.username or parsed.password:
        raise SSRFError("embedded credentials / userinfo are not allowed")

    host = (parsed.hostname or "").lower()
    if not host:
        raise SSRFError("missing host")

    if host not in config.GIT_HOST_ALLOWLIST:
        raise SSRFError(f"host {host!r} is not in the allowlist")

    # Reject a host that is itself a literal private/loopback/etc. IP.
    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        literal = None
    if literal is not None and _ip_is_disallowed(literal):
        raise SSRFError(f"host IP {host!r} is disallowed")

    if resolve:
        try:
            addresses = _resolve_addresses(host)
        except OSError as exc:
            raise SSRFError(f"could not resolve host {host!r}: {exc}") from exc
        for addr in addresses:
            ip = ipaddress.ip_address(addr)
            if _ip_is_disallowed(ip):
                raise SSRFError(f"host {host!r} resolves to disallowed address {addr}")

    return url


def is_blocked_beacon_host(host: str) -> bool:
    """True if an outbound beacon to ``host`` must be refused (§13).

    The bundled compose listener is addressed by hostname and intentionally lives
    on a private bridge network, so that hostname is allowed. Every other host/IP
    is blocked for worker-emitted beacons; git clone SSRF validation is handled
    separately by ``validate_git_url``.
    """
    host = host.strip().lower()
    if not host:
        return True

    return host != "listener"
