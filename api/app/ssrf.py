"""SSRF guard for git URLs (CONTRACTS.md §13).

Accept ONLY if ALL hold:
- scheme is https (exact)
- host (lowercased, no port) is in the exact allowlist
- URL contains no userinfo (@)
- resolved IPs are not private / loopback / link-local / reserved
- explicitly rejects 169.254.169.254 and 169.254.170.2 (metadata IPs)
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

# Exact-host allowlist (no subdomain wildcards per §13 v1)
_ALLOWED_HOSTS: frozenset[str] = frozenset(
    ["github.com", "gitlab.com", "bitbucket.org", "codeberg.org"]
)

# Cloud metadata endpoint IPs — always block even if they somehow pass the
# private/reserved check.
_METADATA_IPS: frozenset[str] = frozenset(["169.254.169.254", "169.254.170.2"])


class SSRFError(ValueError):
    """Raised when a git URL fails the SSRF guard."""


def validate_git_url(url: str) -> None:
    """Raise SSRFError if `url` does not pass the SSRF guard; otherwise return.

    This is the api-side validation.  The worker re-validates before cloning.
    """
    try:
        parsed = urlparse(url)
    except Exception as exc:
        raise SSRFError(f"Unparseable URL: {exc}") from exc

    # 1. Scheme must be https
    if parsed.scheme != "https":
        raise SSRFError(
            f"Only https:// git URLs are allowed; got scheme={parsed.scheme!r}"
        )

    # 2. No userinfo (embedded credentials)
    if parsed.username or parsed.password or "@" in (parsed.netloc or ""):
        raise SSRFError("git URL must not contain userinfo (user:pass@ or @)")

    # 3. Exact host allowlist
    host = (parsed.hostname or "").lower()
    if not host:
        raise SSRFError("git URL has no host")
    if host not in _ALLOWED_HOSTS:
        raise SSRFError(
            f"Host {host!r} is not in the allowlist "
            f"({', '.join(sorted(_ALLOWED_HOSTS))})"
        )

    # 4. Resolve hostname and reject private/loopback/link-local/reserved IPs
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        raise SSRFError(f"Failed to resolve host {host!r}: {exc}") from exc

    for info in infos:
        raw_ip = str(info[4][0])
        # Strip IPv6 zone ID if present (e.g. "::1%lo")
        raw_ip_clean = raw_ip.split("%")[0]
        try:
            addr = ipaddress.ip_address(raw_ip_clean)
        except ValueError as exc:
            raise SSRFError(f"Could not parse resolved IP {raw_ip!r}") from exc

        ip_str = str(addr)

        # Explicit metadata IP block
        if ip_str in _METADATA_IPS:
            raise SSRFError(f"Resolved IP {ip_str} is a cloud metadata endpoint")

        # Private / loopback / link-local / reserved
        if (
            addr.is_private
            or addr.is_loopback
            or addr.is_link_local
            or addr.is_reserved
            or addr.is_multicast
        ):
            raise SSRFError(
                f"Resolved IP {ip_str} is private/loopback/link-local/reserved"
            )
